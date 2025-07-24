// src/pages/Chat.jsx
import { useEffect, useState } from "react";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import { getAuthHeaders, clearTokens } from "../utils/auth";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Uploading from "../components/Uploading";
import ButtonLoading from "../components/ButtonLoading";
import { FaRobot, FaUser} from "react-icons/fa";
import { FiMessageSquare } from "react-icons/fi";

function Chat() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [query, setQuery] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [userDetails, setUserDetails] = useState(null);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false); 
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const API_BASE = "http://127.0.0.1:8000/api/v1";
  const navigate = useNavigate();

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/sessions/sessions`, {
        headers: getAuthHeaders(),
        withCredentials: true,
      });
      if(response.data.sessions.length > 0) {
        response.data.sessions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setSessions(response.data.sessions);
      }
      setLoading(false);
    } catch (error) {
      setLoading(false);
      console.error("Error fetching sessions:", error);
    }
  };

  const createSession = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE}/sessions/sessions`, {}, {
        headers: getAuthHeaders(),
        withCredentials: true,
      });
      setActiveSessionId(response.data.session_id);
      fetchSessions();
      setChatMessages([
        {
          // question: "",
          answer: `Welcome ${userDetails?.username}, upload your document and ask query based on it.`,
        },
      ]);
      setUploadedDocs([]);
      setLoading(false);
    } catch (error) {
      toast.error("Failed to create session. Please try again.");
      setLoading(false);
      setActiveSessionId(null);
      setChatMessages([]);
      setUploadedDocs([]);
      console.error("Error creating session:", error);
    }
  };

  const deleteSession = async (sessionId) => {
    setSessionToDelete(sessionId);
  };

  const confirmDeleteSession = async () => {
  if (!sessionToDelete) return;
    try {
      setLoading(true);
      await axios.delete(`${API_BASE}/sessions/sessions/${sessionToDelete}`, {
        headers: getAuthHeaders(),
        withCredentials: true,
      });
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionToDelete));
      if (activeSessionId === sessionToDelete) {
        setActiveSessionId(null);
        setChatMessages([]);
        setUploadedDocs([]);
      }
      toast.success("Chat deleted successfully.");
    } catch (error) {
      console.error("Error deleting session:", error);
    } finally {
      setLoading(false);
      setSessionToDelete(null); // close modal
    }
  };

  const fetchUserDetails = async () => {
    try {
      const response = await axios.get(`${API_BASE}/auth/me`, {
        headers: getAuthHeaders(),
        withCredentials: true,
      });
      setUserDetails(response.data);
    } catch (error) {
      clearTokens();
      navigate("/login");
    }
  };

  const fetchChatHistory = async (sessionId) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_BASE}/query/history?skip=0&limit=100`,
        { headers: getAuthHeaders(), withCredentials: true }
      );
      const messages = response.data.filter((m) => m.session_id === sessionId).sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      setChatMessages(messages);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      toast.error("Failed to fetch chat history. Please try again.");
      setChatMessages([]);
      console.error("Error fetching chat history:", error);
    }
  };

  const handleNewSession = () => createSession();
  const handleSessionClick = (sessionId) => {
    setActiveSessionId(sessionId);
    fetchChatHistory(sessionId);
  };

  const handleFolderSelect = async (event) => {
    const files = event.target.files;
    if (!files.length || !activeSessionId) {
      toast.error("Select a folder and make sure a session is active.");
      return;
    }

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file, file.webkitRelativePath);
    }
    formData.append("session_id", activeSessionId);

    setUploading(true);
    try {
      const resp = await axios.post(
        `${API_BASE}/upload/batch/upload`,
        formData,
        {
          headers: {
            ...getAuthHeaders(),
            "Content-Type": "multipart/form-data",
          },
          withCredentials: true,
        }
      );
      setUploadedDocs(resp.data.documents.map((f) => f.filename));
      toast.success("Documents uploaded successfully!");
    } catch (err) {
      console.error("Upload error:", err);
      toast.error("Failed to upload folder documents.");
    } finally {
      setUploading(false);
      event.target.value = null;
    }
  };


  // Replace handleUploadClick to simply trigger the hidden input:
  const openFolderPicker = () => {
    if (!activeSessionId) {
      toast.error("Please create or select a session first.");
      return;
    }
    document.getElementById("folderUploader").click();
  };


  const handleSendQuery = async (e) => {
    e.preventDefault();
    if (!query || !activeSessionId) return;

    setSending(true);
    try {
      const response = await axios.post(
        `${API_BASE}/query/search`,
        {
          question: query,
          session_id: activeSessionId,
          include_history: true,
          limit: 2,
        },
        { headers: getAuthHeaders(), withCredentials: true }
      );
      setChatMessages((prev) => [
        ...prev,
        { question: query, answer: response.data.answer },
      ]);

      await fetchSessions();
      setQuery("");
    } catch (error) {
      console.error("Query failed:", error);
      if (error.response?.status === 404) {
        setChatMessages((prev) => [
          ...prev,
          {
            question: query,
            answer:
              "No relevant context found in the uploaded documents. Please try asking something related to the uploaded content.",
          },
        ]);
      }
    } finally {
      setSending(false);
    }
  };


  const handleLogout = () => {
    clearTokens();
    navigate("/login");
  };

  useEffect(() => {
    fetchSessions();
    fetchUserDetails();
  }, []);
  const noSessionSelected = userDetails && !activeSessionId ;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar
        sessions={sessions}
        onNewSession={handleNewSession}
        onSessionClick={handleSessionClick}
        onDeleteSession={deleteSession}
        activeSessionId={activeSessionId}
      />

      <div className="flex-1 p-6 flex flex-col w-full overflow-hidden">
        <ToastContainer position="top-right" autoClose={4000} />
        <div className="flex justify-between items-center p-4 bg-white shadow-md rounded-xl mx-4 mt-4">
          <div>
            {userDetails && (
              <div>
                <p className="font-medium text-gray-700">{userDetails.full_name}</p>
                <p className="text-sm text-gray-500">{userDetails.email}</p>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-4 py-2 rounded-md text-sm hover:bg-white hover:text-red-600 hover:border hover:border-red-500 transition"
          >
            Logout
          </button>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden max-h-[calc(100vh-8rem)] flex flex-col-reverse space-y-4 space-y-reverse px-4">
            {noSessionSelected && (
            <div className="flex flex-1 items-center justify-center">
              <div className="bg-white dark:bg-gray-400 p-8 rounded-2xl shadow-lg border w-full max-w-xl text-center">
                <FiMessageSquare className="mx-auto text-indigo-600 text-6xl mb-4 animate-pulse" />
                <h1 className="text-3xl font-bold mb-2 text-indigo-600 dark:text-white">
                  Welcome to <span className="text-indigo-600">DocQuery</span>
                </h1>
                <p className="text-gray-700 dark:text-black mb-4">
                  Upload your documents and ask questions based on the content.
                </p>
                <p className="text-sm text-gray-500 dark:text-white mb-6">
                  Tip: You can upload multiple formats like PDFs, DOCX, and TXT.
                </p>
                <button
                  onClick={handleNewSession}
                  className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 transition"
                >
                  + New Session
                </button>
              </div>
            </div>
            )}


          {[...chatMessages].reverse().map((msg, idx) => (
            <div key={idx} className="flex flex-col gap-3 w-full px-2">
              {msg.question && (
                <div className="self-end bg-indigo-600 text-white rounded-xl px-4 py-3 shadow-md w-fit max-w-[80%]">
                  <div className="flex items-center gap-2 text-sm">
                    <FaUser className="text-white" />
                    <span>{msg.question}</span>
                  </div>
                </div>
              )}
              {msg.answer && (
                <div className="self-start bg-indigo-100 text-indigo-800 rounded-xl px-4 py-3 shadow-md w-fit max-w-[80%]">
                  <div className="flex items-center gap-2 text-sm">
                    <FaRobot size={40} className="text-blue" />
                    <span>{msg.answer}</span>
                  </div>
                </div>
              )}
            </div>
          ))}

          {uploadedDocs.length > 0 && (
            <div className="mt-4">
              <h3 className="font-semibold text-gray-700 mb-2">📄 Uploaded Documents</h3>
              <ul className="list-disc pl-5 text-sm">
                {uploadedDocs.map((doc, i) => (
                  <li key={i}>{doc}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {activeSessionId && (
          <form onSubmit={handleSendQuery}>
            <div className="p-4 bg-white rounded-xl shadow-lg border-t border-gray-200 flex items-center gap-2 mt-2">
              <input
                disabled={sending}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 transition disabled:bg-gray-100"
                placeholder="Ask a question..."
              />
              {sending ? (
                <div className="flex items-center max-w-6xl justify-center">
                  <ButtonLoading />
                </div>
              ) : (
                <button
                  type="submit"
                  className="bg-indigo-600 text-white px-5 py-2 rounded hover:bg-indigo-700 transition disabled:opacity-50"
                >
                  Send
                </button>
              )}
              <button
                type="button"
                onClick={openFolderPicker}
                className="bg-indigo-100 text-indigo-700 px-4 py-2 rounded hover:bg-white hover:text-indigo-600 hover:border hover:border-indigo-600 transition"
              >
                Upload Docs
              </button>

            </div>
          </form>
        )}
        
        <input
          type="file"
          id="folderUploader"
          webkitdirectory="true"
          directory="true"
          multiple
          hidden
          onChange={handleFolderSelect}
        />
      </div>
      {uploading && <Uploading />}

      {sessionToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-2xl shadow-lg w-96">
            <h2 className="text-lg font-semibold mb-4 text-center">Confirm Deletion</h2>
            <p className="text-gray-700 mb-6 text-center">Are you sure you want to delete this chat?</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setSessionToDelete(null)}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteSession}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-white hover:text-red-600 hover:border hover:border-red-600 transition"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chat;
