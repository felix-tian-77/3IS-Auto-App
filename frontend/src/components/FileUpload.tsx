import { Upload, Button, message } from 'antd';
import { InboxOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { formatFileSize } from '@/utils/format';

const { Dragger } = Upload;

interface FileUploadProps {
  fileList: UploadFile[];
  onChange: (files: UploadFile[]) => void;
}

export default function FileUpload({ fileList, onChange }: FileUploadProps) {
  const beforeUpload = (file: File) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      message.error('仅支持 JPG、PNG、PDF 格式');
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
      <Dragger
        multiple
        fileList={fileList}
        beforeUpload={beforeUpload}
        onChange={({ fileList: newList }) => onChange(newList)}
        showUploadList={false}
        accept=".jpg,.jpeg,.png,.pdf"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持 JPG、PNG、PDF 格式，可多选文件一次提交</p>
      </Dragger>
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
