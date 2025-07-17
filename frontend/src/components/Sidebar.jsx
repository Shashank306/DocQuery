// src/components/Sidebar.jsx
import { useEffect, useState } from "react";
import { MdDelete } from "react-icons/md";

function Sidebar({ sessions = [], onNewSession, onSessionClick, onDeleteSession, activeSessionId }) {
  const [error, setError] = useState(null);
  const [todaySessions, setTodaySessions] = useState([]);
  const [pastSessions, setPastSessions] = useState([]);
  const today = new Date().toISOString().split("T")[0];

  useEffect(() => {
    if (!Array.isArray(sessions)) {
      setError("Invalid sessions data");
      return;
    }

    const todayList = [];
    const pastList = [];

    sessions.forEach((session) => {
      const sessionDate = new Date(session.created_at).toISOString().split("T")[0];
      if (sessionDate === today) {
        todayList.push(session);
      } else {
        pastList.push(session);
      }
    });

    setTodaySessions(todayList);
    setPastSessions(pastList);
  }, [sessions]);

  const renderSession = (session) => (
    <div
      className={`flex justify-between items-center p-2 rounded shadow transition cursor-pointer ${
        activeSessionId === session.session_id ? "bg-blue-500 font-semibold text-white" : "bg-white hover:bg-blue-50"
      }`}
    >
      <div
        className="text-sm cursor-pointer flex w-full flex-col"
        onClick={() => onSessionClick(session.session_id)}
      >
        {new Date(session.created_at).toISOString().split("T")[0] === today
          ? "Today"
          : new Date(session.created_at).toLocaleDateString()}
        <div
          className={`text-xs text-end ${
            activeSessionId === session.session_id ? "text-gray-100" : "text-gray-600"
          }`}
        >
          {new Date(session.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
      <button
        onClick={() => onDeleteSession(session.session_id)}
        className="text-red-500 text-xs ml-2 hover:underline"
        title="Delete chat"
      >
        <MdDelete size={20} className="text-black hover:text-red-700" />
      </button>
    </div>
  );

  if (error) {
    return <div className="p-4 text-red-500">Sidebar error: {error}</div>;
  }

  return (
    <div className="w-64 bg-gray-100 border-r h-screen flex flex-col">
      {/* Header */}
      <div className="sticky top-0 bg-gray-100 z-10 p-4 border-b">
        <h2 className="text-blue-800 text-2xl font-bold mb-2 px-2">DocQuery</h2>
        <button
          className="w-full bg-blue-500 text-white cursor-pointer py-2 rounded hover:bg-white hover:text-blue-500 hover:border hover:border-blue-500 transition duration-200"
          onClick={onNewSession}
        >
          + New Chat
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {todaySessions.length > 0 && <h3 className="text-lg font-semibold mb-2">Today's Sessions</h3>}
        {todaySessions.map((session) => (
          <div key={session.session_id}>{renderSession(session)}</div>
        ))}

        {todaySessions.length === 0 && pastSessions.length === 0 && (
          <p className="text-gray-500 text-sm">No Chat. Create New Chat</p>
        )}

        {pastSessions.length > 0 && pastSessions.map((session) => (
          <div key={session.session_id}>{renderSession(session)}</div>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;
