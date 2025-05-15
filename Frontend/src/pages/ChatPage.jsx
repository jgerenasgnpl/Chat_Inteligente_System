import React from 'react';
import { Layout } from 'antd';
import ChatContainer from '../components/ChatContainer';

const { Content } = Layout;

const ChatPage = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '2rem' }}>
        <ChatContainer />
      </Content>
    </Layout>
  );
};

export default ChatPage;
