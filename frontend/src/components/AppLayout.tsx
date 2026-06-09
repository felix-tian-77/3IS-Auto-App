import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  FormOutlined,
  UnorderedListOutlined,
  DashboardOutlined,
  DesktopOutlined,
} from '@ant-design/icons';

const { Sider, Content } = Layout;

const menuItems = [
  {
    key: 'staff',
    label: '员工门户',
    type: 'group' as const,
    children: [
      {
        key: '/staff/submit',
        icon: <FormOutlined />,
        label: '提交申请',
      },
      {
        key: '/staff/track',
        icon: <UnorderedListOutlined />,
        label: '申请跟踪',
      },
    ],
  },
  {
    key: 'admin',
    label: '管理后台',
    type: 'group' as const,
    children: [
      {
        key: '/admin/dashboard',
        icon: <DashboardOutlined />,
        label: '管理概览',
      },
      {
        key: '/admin/workers',
        icon: <DesktopOutlined />,
        label: '设备监控',
      },
    ],
  },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = location.pathname;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div
          style={{
            height: 48,
            margin: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 700,
            fontSize: collapsed ? 14 : 18,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? '3IS' : '3IS-Auto-App'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
