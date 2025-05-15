import React from "react";
import { List } from "antd";

const MessageList = ({ messages }) => (
  <List
    dataSource={messages}
    renderItem={(msg) => (
      <List.Item style={{ justifyContent: msg.isMine ? "flex-end" : "flex-start" }}>
        <div className={`message ${msg.isMine ? "mine" : "theirs"}`}>{msg.text}</div>
      </List.Item>
    )}
    style={{ maxHeight: 400, overflowY: "auto" }}
  />
);

export default MessageList;
