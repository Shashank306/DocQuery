// src/components/Sidebar.jsx
import { useEffect, useState } from "react";
import { MdDelete } from "react-icons/md";
import { FiMessageCircle } from "react-icons/fi";

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
      className={`flex justify-between items-center p-3 rounded-xl shadow-md transition cursor-pointer ${
        activeSessionId === session.session_id
          ? "bg-indigo-500 text-white font-semibold"
          : "bg-white hover:bg-indigo-500 text-gray-800"
      }`}
    >
      <div
        className="text-sm flex w-full flex-col"
        onClick={() => onSessionClick(session.session_id)}
      >
        <span>
          {session.name
            ? session.name
            : new Date(session.created_at).toISOString().split("T")[0] === today
              ? "Today"
              : new Date(session.created_at).toLocaleDateString()}
        </span>
        <div
          className={`text-xs text-end ${
            activeSessionId === session.session_id ? "text-indigo-100" : "text-gray-500"
          }`}
        >
          {new Date(session.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
      <button
        onClick={() => onDeleteSession(session.session_id)}
        className="ml-2"
        title="Delete chat"
      >
        <MdDelete
          size={22}
          className={`transition ${
            activeSessionId === session.session_id
              ? "text-white hover:text-red-200"
              : " hover:text-red-800"
          }`}
        />
      </button>
    </div>
  );

  if (error) {
    return <div className="p-4 text-red-500">Sidebar error: {error}</div>;
  }

  return (
    <div className="w-64 bg-white shadow-lg rounded-r-2xl h-screen flex flex-col">
      {/* Header */}
      <div className="sticky top-0 bg-white z-10 p-4 border-b rounded-tr-2xl">
        <h2 className="text-indigo-700 text-2xl font-bold mb-3 text-center">DocQuery</h2>
        <button
          className="w-full bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-700 transition"
          onClick={onNewSession}
        >
          + New Chat
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {todaySessions.length > 0 && (
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Today's Sessions</h3>
        )}
        {todaySessions.map((session) => (
          <div key={session.session_id}>{renderSession(session)}</div>
        ))}

        {todaySessions.length === 0 && pastSessions.length === 0 && (
          <div className="flex flex-col items-center justify-center text-gray-400 text-sm mt-6">
            <FiMessageCircle size={24} className="mb-2" />
            <p>No Chat. Create New Chat</p>
          </div>
        )}

        {pastSessions.length > 0 && (
          <>
            <h3 className="text-sm font-semibold text-gray-700 mt-4 mb-2">Past Sessions</h3>
            {pastSessions.map((session) => (
              <div key={session.session_id}>{renderSession(session)}</div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export default Sidebar;
