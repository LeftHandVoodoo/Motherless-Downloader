import { useState, useEffect, useCallback } from 'react';
import { Download, Pause, Play, X, Trash2, Settings } from 'lucide-react';
import { downloadsApi, type DownloadInfo, DownloadStatus, type DownloadRequest } from './lib/api';
import { formatBytes, formatSpeed, calculateETA, cn } from './lib/utils';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import './index.css';

function App() {
  const [downloads, setDownloads] = useState<DownloadInfo[]>([]);
  const [url, setUrl] = useState('');
  const [connections, setConnections] = useState(4);
  const [ws, setWs] = useState<WebSocket | null>(null);

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

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  // Fetch downloads on mount
  useEffect(() => {
    fetchDownloads();
  }, []);

  const fetchDownloads = async () => {
    try {
      const response = await downloadsApi.getAll();
      setDownloads(response.data);
    } catch (error) {
      console.error('Failed to fetch downloads:', error);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              Motherless Downloader
            </h1>
            <p className="text-slate-300">
              Multi-threaded download manager with queue support
            </p>
          </div>
          <Button variant="outline" size="icon" className="bg-white/10 hover:bg-white/20 border-white/20 text-white">
            <Settings className="w-5 h-5" />
          </Button>
        </div>

        {/* Add Download Card */}
        <Card className="bg-white/10 backdrop-blur-lg border-white/20">
          <CardHeader>
            <CardTitle className="text-white">Add New Download</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddDownload} className="space-y-4">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste Motherless URL here..."
                  className="flex-1 px-4 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="number"
                  value={connections}
                  onChange={(e) => setConnections(parseInt(e.target.value))}
                  min="1"
                  max="30"
                  className="w-24 px-4 py-2 rounded-md bg-white/10 border border-white/20 text-white text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                  title="Connections"
                />
                <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                  <Download className="w-4 h-4 mr-2" />
                  Add
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Downloads Queue */}
        <Card className="bg-white/10 backdrop-blur-lg border-white/20">
          <CardHeader>
            <CardTitle className="text-white">
              Download Queue ({downloads.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {downloads.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
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

        {/* Footer */}
        <div className="text-center text-slate-400 text-sm">
          <p>Version 0.2.0 • Modern FastAPI + React Interface</p>
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
    <div className="bg-white/5 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className={cn("w-2 h-2 rounded-full", statusColor)} />
            <span className="text-sm font-medium text-white capitalize">
              {download.status}
            </span>
          </div>
          <p className="text-white text-sm font-medium truncate">
            {download.filename || new URL(download.url).pathname.split('/').pop()}
          </p>
          <p className="text-slate-400 text-xs truncate">
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
              className="h-8 w-8 text-white hover:bg-white/10"
            >
              <Pause className="w-4 h-4" />
            </Button>
          )}
          {download.status === DownloadStatus.PAUSED && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onResume(download.id)}
              className="h-8 w-8 text-white hover:bg-white/10"
            >
              <Play className="w-4 h-4" />
            </Button>
          )}
          {(download.status === DownloadStatus.DOWNLOADING || download.status === DownloadStatus.PAUSED) && (
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onCancel(download.id)}
              className="h-8 w-8 text-white hover:bg-white/10"
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
        <div className="w-full bg-white/10 rounded-full h-2">
          <div
            className={cn("h-2 rounded-full transition-all duration-300", statusColor)}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-slate-300">
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
        <div className="text-red-400 text-xs bg-red-500/10 px-3 py-2 rounded">
          {download.error_message}
        </div>
      )}
    </div>
  );
}

export default App;
