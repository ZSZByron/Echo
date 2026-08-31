/**
 * UploadToolbar Component
 *
 * Glass-panel toolbar section for worldview document upload.
 * Renders between seed cards grid and custom input panel.
 */

import { useState, useRef, useEffect } from 'react';
import '../../components/theme.css';

interface UploadToolbarProps {
  onUpload: (filename: string, content: string) => void;
  isUploading: boolean;
  uploadError: string | null;
}

export function UploadToolbar({ onUpload, isUploading, uploadError }: UploadToolbarProps) {
  const [uploadStage, setUploadStage] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadStages = ['格式检测中', '版权比对中', '解析填充中'];

  // Cycle through upload stages during upload
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isUploading) {
      setUploadStage(0);
      interval = setInterval(() => {
        setUploadStage(prev => (prev + 1) % uploadStages.length);
      }, 1500); // Change stage every 1.5 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isUploading, uploadStages.length]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setLocalError(null);

    // Validate file size (2MB limit)
    const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB in bytes
    if (file.size > MAX_FILE_SIZE) {
      setLocalError('文件超过 2MB 上限，请精简后重试');
      return;
    }

    // Validate file type
    const validExtensions = ['.txt', '.md'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExtensions.includes(fileExtension)) {
      setLocalError('仅支持 .txt 和 .md 纯文本文件');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result;
      const content = typeof result === 'string' ? result : '';
      if (!content.trim()) {
        setLocalError('文件内容为空，无法解析');
        return;
      }
      onUpload(file.name, content);
    };
    reader.onerror = () => {
      setLocalError('文件读取失败，请重试');
    };
    reader.readAsText(file, 'UTF-8');

    // Reset input so re-selecting the same file re-triggers change.
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="glass-panel p-6 mb-8">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h2 className="text-stardust-300 text-lg font-medium mb-2">上传世界观文档</h2>
          <p className="text-void-400 text-sm">
            支持 .txt 和 .md 格式（最大 2MB）— AI 将检测版权风险并自动填充 10 模块
          </p>
        </div>

        <div className="flex items-center gap-4">
          {isUploading ? (
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-stardust-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-stardust-300 text-sm">
                {uploadStages[uploadStage % uploadStages.length]}
              </span>
            </div>
          ) : (
            <>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-all glow-starlight flex items-center gap-2"
              >
                <span>⇪</span>
                <span>上传世界观文档</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md"
                onChange={handleFileSelect}
                className="hidden"
                disabled={isUploading}
              />
            </>
          )}
        </div>
      </div>

      {(uploadError || localError) && (
        <div className="mt-4 glass-panel p-3 bg-cosmos-error/10 border-cosmos-error/30">
          <p className="text-cosmos-error text-sm">{uploadError || localError}</p>
        </div>
      )}
    </div>
  );
}
