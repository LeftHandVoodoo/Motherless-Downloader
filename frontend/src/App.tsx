import { useState, useEffect } from 'react';
import { Download, Pause, Play, X, Trash2, Settings, History, List, RotateCcw } from 'lucide-react';
import { downloadsApi, settingsApi, type DownloadInfo, DownloadStatus, type DownloadRequest } from './lib/api';
import { formatBytes, formatSpeed, calculateETA, cn } from './lib/utils';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import './index.css';

type ViewMode = 'queue' | 'history';

function App() {
  const [downloads, setDownloads] = useState<DownloadInfo[]>([]);
  const [url, setUrl] = useState('');
  const [connections, setConnections] = useState(4);
  const [showSettings, setShowSettings] = useState(false);
  const [downloadDir, setDownloadDir] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('queue');

  // WebSocket connection
  useEffect(() => {
    const websocket = new WebSocket(`ws://${window.location.host}/ws`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'progress') {
        setDownloads(prev => {
          const index = prev.findIndex(d => d.id === message.data.id);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = message.data;
            return updated;
          }
          return [...prev, message.data];
        });
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      websocket.close();
    };
  }, []);

  // Fetch downloads and settings on mount
  useEffect(() => {
    fetchDownloads();
    fetchSettings();
  }, []);

  const fetchDownloads = async () => {
    try {
      const response = await downloadsApi.getAll();
      setDownloads(response.data);
    } catch (error) {
      console.error('Failed to fetch downloads:', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await settingsApi.get();
      setDownloadDir(response.data.download_dir || '');
      setConnections(response.data.default_connections || 4);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  };

  const handleBrowseDirectory = async () => {
    // Use File System Access API if available (Chrome/Edge)
    if ('showDirectoryPicker' in window) {
      try {
        const dirHandle = await (window as any).showDirectoryPicker();
        const dirName = dirHandle.name;
        
        // Try to get the path - File System Access API has limitations
        // We can request permission and use the directory handle
        // For now, prompt user to enter the full path
        const userPath = prompt(
          `Selected directory: ${dirName}\n\nPlease enter the full path to this directory:\n(e.g., C:\\Users\\YourName\\Downloads)`,
          downloadDir || ''
        );
        
        if (userPath && userPath.trim()) {
          // Validate the path with the backend
          try {
            const response = await fetch('/api/settings/validate-dir', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ path: userPath.trim() }),
            });
            const result = await response.json();
            
            if (result.valid) {
              setDownloadDir(result.path);
            } else {
              alert(`Invalid directory: ${result.error}`);
            }
          } catch (error) {
            console.error('Failed to validate directory:', error);
            // Still set it, let the save operation validate
            setDownloadDir(userPath.trim());
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Failed to browse directory:', error);
          alert('Failed to open directory picker. Please enter the path manually.');
        }
      }
    } else {
      // Fallback: Prompt for path
      const userPath = prompt(
        'Enter the full path to the download directory:\n(e.g., C:\\Users\\YourName\\Downloads)',
        downloadDir || ''
      );
      if (userPath && userPath.trim()) {
        // Validate the path
        try {
          const response = await fetch('/api/settings/validate-dir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: userPath.trim() }),
          });
          const result = await response.json();
          
          if (result.valid) {
            setDownloadDir(result.path);
          } else {
            alert(`Invalid directory: ${result.error}`);
          }
        } catch (error) {
          console.error('Failed to validate directory:', error);
          setDownloadDir(userPath.trim());
        }
      }
    }
  };

  const handleSaveSettings = async () => {
    try {
      await settingsApi.update({
        download_dir: downloadDir,
        default_connections: connections,
        adaptive_default: true,
      });
      setShowSettings(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    }
  };

  const handleAddDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    try {
      const request: DownloadRequest = {
        url: url.trim(),
        connections,
        adaptive: true,
      };

      await downloadsApi.create(request);
      setUrl('');
      // Download will be added via WebSocket update
    } catch (error) {
      console.error('Failed to add download:', error);
      alert('Failed to add download. Please check the URL and try again.');
    }
  };

  const handlePause = async (id: string) => {
    try {
      await downloadsApi.pause(id);
    } catch (error) {
      console.error('Failed to pause download:', error);
    }
  };

  const handleResume = async (id: string) => {
    try {
      await downloadsApi.resume(id);
    } catch (error) {
      console.error('Failed to resume download:', error);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await downloadsApi.cancel(id);
    } catch (error) {
      console.error('Failed to cancel download:', error);
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await downloadsApi.remove(id);
      setDownloads(prev => prev.filter(d => d.id !== id));
    } catch (error) {
      console.error('Failed to remove download:', error);
    }
  };

  const handleClearCompleted = async () => {
    try {
      const response = await downloadsApi.cleanup();
      console.log(`Cleared ${response.data.removed} completed downloads`);
      // Refresh download list
      fetchDownloads();
    } catch (error) {
      console.error('Failed to clear completed downloads:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-gray-900 to-zinc-950">
      {/* Banner Header */}
      <div className="w-full bg-zinc-900/50 border-b border-zinc-800 mb-6 relative">
        <img 
          src="/banner.png" 
          alt="Motherless Downloader" 
          className="w-full h-auto max-h-32 object-contain px-6 py-3"
        />
        <Button 
          variant="outline" 
          size="icon" 
          className="absolute top-4 right-6 bg-zinc-800/80 hover:bg-zinc-700/80 border-zinc-700 text-gray-300 hover:text-white"
          onClick={() => setShowSettings(!showSettings)}
        >
          <Settings className="w-5 h-5" />
        </Button>
      </div>

      <div className="max-w-6xl mx-auto px-6 space-y-6">

        {/* View Mode Tabs */}
        <div className="flex gap-2 border-b-2 border-zinc-700 pb-3 mb-4">
          <Button
            variant={viewMode === 'queue' ? 'default' : 'ghost'}
            onClick={() => setViewMode('queue')}
            className={viewMode === 'queue' 
              ? 'bg-zinc-700 text-white hover:bg-zinc-600 px-6 py-2' 
              : 'text-gray-400 hover:text-gray-200 hover:bg-zinc-800/50 px-6 py-2'
            }
          >
            <List className="w-4 h-4 mr-2" />
            Download Queue
          </Button>
          <Button
            variant={viewMode === 'history' ? 'default' : 'ghost'}
            onClick={() => setViewMode('history')}
            className={viewMode === 'history' 
              ? 'bg-zinc-700 text-white hover:bg-zinc-600 px-6 py-2' 
              : 'text-gray-400 hover:text-gray-200 hover:bg-zinc-800/50 px-6 py-2'
            }
          >
            <History className="w-4 h-4 mr-2" />
            History
          </Button>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardHeader>
              <CardTitle className="text-gray-100">Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Download Directory
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={downloadDir}
                    onChange={(e) => setDownloadDir(e.target.value)}
                    className="flex-1 px-4 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-zinc-500"
                    placeholder="e.g., C:\Downloads"
                  />
                  <Button
                    type="button"
                    onClick={handleBrowseDirectory}
                    variant="outline"
                    className="bg-zinc-800 hover:bg-zinc-700 border-zinc-600 text-gray-300 whitespace-nowrap"
                  >
                    Browse
                  </Button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Default Connections: {connections}
                </label>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={connections}
                  onChange={(e) => setConnections(parseInt(e.target.value))}
                  className="w-full accent-zinc-500"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleSaveSettings}
                  className="bg-zinc-700 hover:bg-zinc-600 text-white"
                >
                  Save Settings
                </Button>
                <Button
                  onClick={() => setShowSettings(false)}
                  variant="outline"
                  className="bg-zinc-800 hover:bg-zinc-700 border-zinc-600 text-gray-300"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Queue View */}
        {viewMode === 'queue' && (
          <>
        {/* Add Download Card */}
        <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
          <CardHeader>
            <CardTitle className="text-gray-100">Add New Download</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddDownload} className="space-y-4">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste Motherless URL here..."
                  className="flex-1 px-4 py-2 rounded-md bg-zinc-800 border border-zinc-600 text-gray-100 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-zinc-500"
                />
                <input
                  type="number"
                  value={connections}
                  onChange={(e) => setConnections(parseInt(e.target.value))}
                  min="1"
                  max="30"
                  className="w-24 px-4 py-2 rounded-md bg-zinc-800 border border-zinc-600 text-gray-100 text-center focus:outline-none focus:ring-2 focus:ring-zinc-500"
                  title="Connections"
                />
                <Button type="submit" className="bg-zinc-700 hover:bg-zinc-600">
                  <Download className="w-4 h-4 mr-2" />
                  Add
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Statistics Panel */}
        {downloads.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-gray-100">
                    {downloads.length}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">Total Downloads</div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-400">
                    {downloads.filter(d => d.status === DownloadStatus.DOWNLOADING).length}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">Active</div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-400">
                    {downloads.filter(d => d.status === DownloadStatus.COMPLETED).length}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">Completed</div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-400">
                    {downloads.filter(d => d.status === DownloadStatus.FAILED).length}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">Failed</div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Downloads Queue */}
        <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-gray-100">
                Download Queue ({downloads.length})
              </CardTitle>
              {downloads.some(d => d.status === DownloadStatus.COMPLETED || d.status === DownloadStatus.FAILED || d.status === DownloadStatus.CANCELLED) && (
                <Button
                  onClick={handleClearCompleted}
                  variant="outline"
                  size="sm"
                  className="bg-zinc-800 hover:bg-zinc-700 border-zinc-600 text-gray-300"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear Completed
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {downloads.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No downloads yet. Add a URL above to get started.
              </div>
            ) : (
              downloads.map((download) => (
                <DownloadItem
                  key={download.id}
                  download={download}
                  onPause={handlePause}
                  onResume={handleResume}
                  onCancel={handleCancel}
                  onRemove={handleRemove}
                />
              ))
            )}
          </CardContent>
        </Card>
          </>
        )}

        {/* History View */}
        {viewMode === 'history' && <HistoryView onSwitchToQueue={() => setViewMode('queue')} />}

        {/* Footer */}
        <div className="text-center text-gray-500 text-sm pb-6">
          <p>Version 0.3.2 • Modern FastAPI + React Interface</p>
        </div>
      </div>
    </div>
  );
}

interface DownloadItemProps {
  download: DownloadInfo;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  onRemove: (id: string) => void;
}

function DownloadItem({ download, onPause, onResume, onCancel, onRemove }: DownloadItemProps) {
  const progress = download.total_bytes > 0
    ? (download.received_bytes / download.total_bytes) * 100
    : 0;

  const eta = calculateETA(download.received_bytes, download.total_bytes, download.speed_bps);

  const statusColor = {
    [DownloadStatus.QUEUED]: 'bg-yellow-500',
    [DownloadStatus.DOWNLOADING]: 'bg-blue-500',
    [DownloadStatus.PAUSED]: 'bg-orange-500',
    [DownloadStatus.COMPLETED]: 'bg-green-500',
    [DownloadStatus.FAILED]: 'bg-red-500',
    [DownloadStatus.CANCELLED]: 'bg-gray-500',
  }[download.status];

  return (
    <div className="bg-zinc-800/60 rounded-lg p-4 space-y-3 border border-zinc-700/50">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className={cn("w-2 h-2 rounded-full", statusColor)} />
            <span className="text-sm font-medium text-gray-200 capitalize">
              {download.status}
            </span>
          </div>
          <p className="text-gray-100 text-sm font-medium truncate">
            {download.filename || new URL(download.url).pathname.split('/').pop()}
          </p>
          <p className="text-gray-500 text-xs truncate">
            {download.url}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-1 ml-4">
          {download.status === DownloadStatus.DOWNLOADING && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onPause(download.id)}
              className="h-8 w-8 text-gray-300 hover:bg-zinc-700 hover:text-white"
            >
              <Pause className="w-4 h-4" />
            </Button>
          )}
          {download.status === DownloadStatus.PAUSED && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onResume(download.id)}
              className="h-8 w-8 text-gray-300 hover:bg-zinc-700 hover:text-white"
            >
              <Play className="w-4 h-4" />
            </Button>
          )}
          {(download.status === DownloadStatus.DOWNLOADING || download.status === DownloadStatus.PAUSED) && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onCancel(download.id)}
              className="h-8 w-8 text-gray-300 hover:bg-zinc-700 hover:text-white"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
          {(download.status === DownloadStatus.COMPLETED ||
            download.status === DownloadStatus.FAILED ||
            download.status === DownloadStatus.CANCELLED) && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onRemove(download.id)}
              className="h-8 w-8 text-red-400 hover:bg-red-500/20"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="w-full bg-zinc-700/50 rounded-full h-2">
          <div
            className={cn("h-2 rounded-full transition-all duration-300", statusColor)}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>
            {formatBytes(download.received_bytes)} / {formatBytes(download.total_bytes)}
          </span>
          <span>{progress.toFixed(1)}%</span>
          {download.status === DownloadStatus.DOWNLOADING && (
            <>
              <span>{formatSpeed(download.speed_bps)}</span>
              <span>ETA: {eta}</span>
              <span>{download.connections} connections</span>
            </>
          )}
        </div>
      </div>

      {/* Error Message */}
      {download.error_message && (
        <div className="text-red-400 text-xs bg-red-900/30 px-3 py-2 rounded border border-red-800/50">
          {download.error_message}
        </div>
      )}
    </div>
  );
}

interface HistoryItem {
  id: string;
  url: string;
  filename: string;
  url_filename: string | null;
  dest_path: string;
  status: string;
  total_bytes: number;
  received_bytes: number;
  speed_bps: number;
  connections: number;
  adaptive: boolean;
  error_message: string | null;
  thumbnail_path: string | null;
  file_exists: boolean;
  created_at: string;
  completed_at: string | null;
  updated_at: string;
}

interface HistoryStats {
  total: number;
  completed: number;
  failed: number;
  cancelled: number;
  total_bytes: number;
  completed_bytes: number;
}

interface HistoryViewProps {
  onSwitchToQueue?: () => void;
}

function HistoryView({ onSwitchToQueue }: HistoryViewProps) {
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [dbPath, setDbPath] = useState<string>('');

  useEffect(() => {
    fetchHistory();
    fetchStats();
    fetchDbPath();
  }, [searchTerm, statusFilter]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: '50',
        offset: '0',
      });
      if (statusFilter) params.append('status', statusFilter);
      if (searchTerm) params.append('search', searchTerm);

      const response = await fetch(`/api/history?${params}`);
      const data = await response.json();
      setHistoryItems(data.items || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/history/statistics');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const fetchDbPath = async () => {
    try {
      const response = await fetch('/api/history/db-path');
      const data = await response.json();
      setDbPath(data.path || '');
    } catch (error) {
      console.error('Failed to fetch database path:', error);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this item from history?')) return;

    try {
      await fetch(`/api/history/${id}`, { method: 'DELETE' });
      setHistoryItems(prev => prev.filter(item => item.id !== id));
      fetchStats();
    } catch (error) {
      console.error('Failed to delete history item:', error);
    }
  };

  const handleRedownload = async (id: string) => {
    try {
      const response = await fetch(`/api/history/${id}/redownload`, { method: 'POST' });
      if (response.ok) {
        await response.json(); // Download queued successfully
        // Switch to queue view to see the new download
        if (onSwitchToQueue) {
          onSwitchToQueue();
        }
      } else {
        const error = await response.json();
        alert(`Failed to redownload: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to redownload:', error);
      alert('Failed to redownload. Please check the console for details.');
    }
  };

  const handleClearOld = async () => {
    if (!confirm('Clear downloads older than 30 days?')) return;

    try {
      const response = await fetch('/api/history/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days: 30 }),
      });
      const data = await response.json();
      alert(`Cleared ${data.removed} old downloads`);
      fetchHistory();
      fetchStats();
    } catch (error) {
      console.error('Failed to clear old history:', error);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <>
      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-100">{stats.total}</div>
                <div className="text-xs text-gray-400 mt-1">Total</div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{stats.completed}</div>
                <div className="text-xs text-gray-400 mt-1">Completed</div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-400">{stats.failed}</div>
                <div className="text-xs text-gray-400 mt-1">Failed</div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-400">{stats.cancelled}</div>
                <div className="text-xs text-gray-400 mt-1">Cancelled</div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">{formatBytes(stats.total_bytes)}</div>
                <div className="text-xs text-gray-400 mt-1">Total Size</div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{formatBytes(stats.completed_bytes)}</div>
                <div className="text-xs text-gray-400 mt-1">Downloaded</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by URL or filename..."
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-zinc-500"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-zinc-500"
            >
              <option value="">All Status</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
            <Button
              onClick={handleClearOld}
              variant="outline"
              className="bg-zinc-800 hover:bg-zinc-700 border-zinc-600 text-gray-300 whitespace-nowrap"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Old (30d+)
            </Button>
          </div>
          {dbPath && (
            <div className="mt-4 pt-4 border-t border-zinc-700">
              <div className="text-xs text-gray-400">
                <span className="text-gray-500">Database:</span>{' '}
                <code className="px-2 py-1 bg-zinc-800 rounded text-gray-300 break-all">
                  {dbPath}
                </code>
                <span className="ml-2 text-gray-500">
                  (You can open this file with any SQLite viewer)
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* History List */}
      <Card className="bg-zinc-900/90 backdrop-blur-sm border-zinc-700">
        <CardHeader>
          <CardTitle className="text-gray-100">Download History ({historyItems.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading...</div>
          ) : historyItems.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No history items found.
            </div>
          ) : (
            historyItems.map((item) => (
              <div
                key={item.id}
                className="bg-zinc-800/60 rounded-lg p-4 space-y-2 border border-zinc-700/50"
              >
                <div className="flex items-start gap-4">
                  {/* Thumbnail */}
                  {item.thumbnail_path && (
                    <div className="flex-shrink-0">
                      <img
                        src={`/api/history/${item.id}/thumbnail`}
                        alt={item.filename || 'Thumbnail'}
                        className="w-32 h-20 object-cover rounded border border-zinc-700 cursor-pointer hover:opacity-80 transition-opacity"
                        title="Double-click to open in VLC"
                        onError={(e) => {
                          // Hide image on error
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                        onDoubleClick={async () => {
                          try {
                            const response = await fetch(`/api/history/${item.id}/open`, {
                              method: 'POST',
                            });
                            if (!response.ok) {
                              const error = await response.json();
                              alert(`Failed to open file: ${error.detail || 'Unknown error'}`);
                            }
                          } catch (error) {
                            console.error('Failed to open file in VLC:', error);
                            alert('Failed to open file in VLC. Please check the console for details.');
                          }
                        }}
                      />
                    </div>
                  )}
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <div
                            className={cn(
                              'w-2 h-2 rounded-full',
                              item.status === 'COMPLETED' && 'bg-green-500',
                              item.status === 'FAILED' && 'bg-red-500',
                              item.status === 'CANCELLED' && 'bg-gray-500'
                            )}
                          />
                          <span className="text-sm font-medium text-gray-200">
                            {item.status}
                          </span>
                        </div>
                        <p className="text-gray-100 text-sm font-medium truncate">
                          {item.filename || (item.dest_path ? item.dest_path.split(/[/\\]/).pop() : null) || item.url_filename || new URL(item.url).pathname.split('/').pop()}
                        </p>
                        <div className="flex items-center gap-2 text-xs">
                          <p className="text-gray-500 truncate">{item.url}</p>
                          {item.dest_path && (
                            <>
                              <span className="text-gray-600">•</span>
                              <span className={item.file_exists ? 'text-green-400' : 'text-red-400'}>
                                {item.file_exists ? '✓ File exists' : '✗ File missing'}
                              </span>
                            </>
                          )}
                        </div>
                        {item.dest_path && (
                          <p className="text-gray-600 text-xs truncate" title={item.dest_path}>
                            {item.dest_path}
                          </p>
                        )}
                      </div>
                      
                      {/* Actions */}
                      <div className="flex gap-1 ml-4">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleRedownload(item.id)}
                          className="h-8 w-8 text-blue-400 hover:bg-blue-500/20"
                          title="Redownload"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleDelete(item.id)}
                          className="h-8 w-8 text-red-400 hover:bg-red-500/20"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-400">
                  <div>
                    <span className="text-gray-500">Size:</span>{' '}
                    {formatBytes(item.total_bytes)}
                  </div>
                  <div>
                    <span className="text-gray-500">Downloaded:</span>{' '}
                    {formatBytes(item.received_bytes)}
                  </div>
                  <div>
                    <span className="text-gray-500">Created:</span>{' '}
                    {formatDate(item.created_at)}
                  </div>
                  <div>
                    <span className="text-gray-500">Completed:</span>{' '}
                    {formatDate(item.completed_at)}
                  </div>
                </div>

                {/* Error Message */}
                {item.error_message && (
                  <div className="text-red-400 text-xs bg-red-900/30 px-3 py-2 rounded border border-red-800/50">
                    {item.error_message}
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </>
  );
}

export default App;
