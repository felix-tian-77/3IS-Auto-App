import { useState, useEffect, useRef, useCallback } from 'react';
import { Upload, Button, message } from 'antd';
import { InboxOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { formatFileSize } from '@/utils/format';

interface SingleFileUploadProps {
  file: UploadFile | null;
  onChange: (file: UploadFile | null) => void;
  accept?: string;
}

export function SingleFileUpload({ file, onChange, accept = ".jpg,.jpeg,.png" }: SingleFileUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileRef = useRef<File | null>(null);

  useEffect(() => {
    if (file && file.originFileObj) {
      const fileObj = file.originFileObj as File;
      fileRef.current = fileObj;
      const url = URL.createObjectURL(fileObj);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else if (file && fileRef.current) {
      const url = URL.createObjectURL(fileRef.current);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
      fileRef.current = null;
    }
  }, [file]);

  const beforeUpload = useCallback((uploadFile: File) => {
    const allowedTypes = ['image/jpeg', 'image/png'];
    if (!allowedTypes.includes(uploadFile.type)) {
      message.error('仅支持 JPG、PNG 格式');
      return Upload.LIST_IGNORE;
    }
    const maxSize = 20 * 1024 * 1024;
    if (uploadFile.size > maxSize) {
      message.error('文件大小不能超过 20MB');
      return Upload.LIST_IGNORE;
    }
    fileRef.current = uploadFile;
    const newFile = {
      ...uploadFile,
      uid: `-${Date.now()}`,
      name: uploadFile.name,
      status: 'done',
      originFileObj: uploadFile,
    } as unknown as UploadFile;
    onChange(newFile);
    return false;
  }, [onChange]);

  const handleRemove = () => {
    onChange(null);
  };

  return (
    <div>
      {!file ? (
        <Upload.Dragger
          fileList={[]}
          beforeUpload={beforeUpload}
          showUploadList={false}
          accept={accept}
          style={{ padding: '16px 0' }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击上传</p>
          <p className="ant-upload-hint">支持 JPG、PNG 格式</p>
        </Upload.Dragger>
      ) : (
        <div
          style={{
            position: 'relative',
            border: '1px solid #b7eb8f',
            borderRadius: 6,
            overflow: 'hidden',
          }}
        >
          <img
            src={previewUrl || ''}
            alt="preview"
            style={{ width: '100%', height: 120, objectFit: 'cover', display: 'block' }}
          />
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={handleRemove}
            style={{ position: 'absolute', top: 4, right: 4, background: 'rgba(255,255,255,0.8)' }}
          />
        </div>
      )}
    </div>
  );
}

interface FileUploadProps {
  fileList: UploadFile[];
  onChange: (files: UploadFile[]) => void;
}

export default function FileUpload({ fileList, onChange }: FileUploadProps) {
  const beforeUpload = (file: File) => {
    const allowedTypes = ['image/jpeg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      message.error('仅支持 JPG、PNG 格式');
      return Upload.LIST_IGNORE;
    }
    const maxSize = 20 * 1024 * 1024;
    if (file.size > maxSize) {
      message.error('文件大小不能超过 20MB');
      return Upload.LIST_IGNORE;
    }
    return false;
  };

  const handleRemove = (uid: string) => {
    onChange(fileList.filter((f) => f.uid !== uid));
  };

  return (
    <div>
      <Upload.Dragger
        multiple
        fileList={fileList}
        beforeUpload={beforeUpload}
        onChange={({ fileList: newList }) => onChange(newList)}
        showUploadList={false}
        accept=".jpg,.jpeg,.png"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持 JPG、PNG 格式，可多选文件一次提交</p>
      </Upload.Dragger>
      {fileList.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {fileList.map((file) => (
            <div
              key={file.uid}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                background: '#f6ffed',
                border: '1px solid #b7eb8f',
                borderRadius: 6,
                marginBottom: 4,
                fontSize: 13,
              }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                {file.name}
                {file.size ? ` (${formatFileSize(file.size)})` : ''}
              </span>
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => handleRemove(file.uid)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
