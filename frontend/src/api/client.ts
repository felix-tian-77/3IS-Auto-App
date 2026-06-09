import axios from 'axios';
import { message } from 'antd';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const msg = error.response.data?.detail || error.response.statusText;
      message.error(msg || '请求失败，请稍后重试');
    } else if (error.request) {
      message.error('网络连接失败，请检查网络');
    } else {
      message.error('请求发送失败');
    }
    return Promise.reject(error);
  }
);

export default client;
