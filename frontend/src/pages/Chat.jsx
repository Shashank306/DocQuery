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
import { FaRobot } from "react-icons/fa";
import { FaUser } from "react-icons/fa";

function Chat() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [query, setQuery] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [userDetails, setUserDetails] = useState(null);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [showWelcome, setShowWelcome] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [folderPathInput, setFolderPathInput] = useState("");
  const [loading, setLoading] = useState(false); 
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
        //sort by new 
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
          question: "",
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
    setLoading(true);
    const confirmed = window.confirm("Are you sure you want to delete this chat?");
    if (!confirmed) return;

    try {
      await axios.delete(`${API_BASE}/sessions/sessions/${sessionId}`, {
        headers: getAuthHeaders(),
        withCredentials: true,
      });
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setChatMessages([]);
        setUploadedDocs([]);
      }
      
      toast.success("Chat deleted successfully.");
    } catch (error) {
      setLoading(false);
      console.error("Error deleting session:", error);
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
        return;
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

  const handleUploadClick = () => {
    
    if (!activeSessionId) {
      toast.error("Please create or select a session first.");
      return;
    }
    setShowModal(true);
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();

    // Step 1: Close modal first
    setShowModal(false);

    // Step 2: Start showing Uploading component
    setLoading(true);

    if (!folderPathInput || !activeSessionId) return;

    try {
      const response = await axios.post(
        `${API_BASE}/upload/batch/folder`,
        { folder_path: folderPathInput, session_id: activeSessionId },
        { headers: getAuthHeaders(), withCredentials: true }
      );

      setUploadedDocs(response.data.files || []);

      // Step 3: Upload complete — stop loading and show toast
      setLoading(false);
      toast.success("Documents uploaded successfully!");
    } catch (error) {
      setLoading(false);
      console.error("Upload error:", error);
      toast.error("Document upload failed.");
    } finally {
      setFolderPathInput("");  // reset input
    }
  };


  const handleSendQuery = async (e) => {
    e.preventDefault();
    setLoading(true);
    if (!query || !activeSessionId) return;
    try {
      const response = await axios.post(
        `${API_BASE}/query/search`,
        {
          question: query,
          session_id: activeSessionId,
          include_history: true,
          limit: 3,
        },
        { headers: getAuthHeaders(), withCredentials: true }
      );

      setChatMessages((prev) => [
        ...prev,
        { question: query, answer: response.data.answer },
      ]);
      setLoading(false);
      setQuery("");
    } catch (error) {
      setLoading(false);

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

  useEffect(() => {
    if (userDetails && showWelcome) {
      setChatMessages([
        {
          question: "",
          answer: `Welcome ${userDetails.username}, upload your document and ask query based on it.`,
        },
      ]);
      setShowWelcome(false);
    }
  }, [userDetails]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        onNewSession={handleNewSession}
        onSessionClick={handleSessionClick}
        onDeleteSession={deleteSession}
        activeSessionId={activeSessionId}
      />

      <div className="flex-1 p-6 flex flex-col w-full overflow-hidden">
        <ToastContainer position="top-right" autoClose={4000} />
        <div className="flex justify-between text-sm text-gray-600 p-4 border-b">
          <div>
            {userDetails && (
              <>
                <div>Name : {userDetails.full_name}</div>
                <div className="text-xs text-gray-500">{userDetails.email}</div>

                {/* {activeSessionId && (
                  <div className="text-xs text-gray-500">Session ID: <code className="bg-gray-200 px-1 rounded">{activeSessionId}</code></div>
                )} */}
              </>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-3 py-1 rounded text-sm cursor-pointer hover:bg-white hover:text-red-500 hover:border-1 hover:border-red-500 transition duration-200"
          >
            Logout
          </button>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden max-h-[calc(100vh-8rem)] flex flex-col-reverse space-y-4 space-y-reverse px-4">
          {[...chatMessages].reverse().map((msg, idx) => (
            <div key={idx} className="flex flex-col gap-2 w-full px-2">
              {msg.question && (
                <div className="self-end bg-blue-100 text-black rounded-lg px-4 py-2 shadow w-fit max-w-[90%]">
                  <FaUser className="text-blue-700 mt-1" />
                  <span>{msg.question}</span>
                </div>
              )}
              {msg.answer && (
                <div className="self-start bg-gray-100 text-black rounded-lg px-4 py-2 shadow w-fit max-w-[90%]">
                  <FaRobot className="text-blue-600 mt-1" /> 
                  <span>{msg.answer}</span>
                </div>
              )}
            </div>
          ))}

          {uploadedDocs.length > 0 && (
            <div className="mt-4">
              <h3 className="font-semibold">Uploaded Documents:</h3>
              <ul className="list-disc pl-5 text-sm">
                {uploadedDocs.map((doc, i) => (
                  <li key={i}>{doc}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {activeSessionId && (
          <form onSubmit={e=> handleSendQuery(e)}>
            <div className="p-4 border-t flex items-center gap-2">
            <input
            disabled={loading}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 p-2 border rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed "
              placeholder="Ask a question..."
            />
           {loading && <div className="flex items-center max-w-6xl justify-center">
              <ButtonLoading />
            </div>}
           {!loading && ( <button
            type="submit"
              className="bg-blue-500 text-white px-4 py-2 rounded-r cursor-pointer hover:bg-white hover:text-blue-500 hover:border-1 hover:border-blue-500 transition duration-200"
            >
              Send
            </button> )}
            <button
              onClick={handleUploadClick}
              className=" bg-green-500 text-white px-4 py-2 rounded cursor-pointer hover:bg-white hover:text-green-500 hover:border-1 hover:border-green-500 transition duration-200"
            >
              Upload Docs
            </button>
          </div>
          </form>
        )}
        {showModal && loading &&(
          <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 w-96">
              <h2 className="text-lg font-semibold mb-4">Upload Folder Path</h2>
              <form onSubmit={handleUploadSubmit}>
                <input
                  type="text"
                  value={folderPathInput}
                  onChange={(e) => setFolderPathInput(e.target.value)}
                  className="w-full p-2 border rounded mb-4"
                  placeholder="Enter folder path"
                  required
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="bg-gray-300 text-gray-800 px-4 py-2 rounded cursor-pointer hover:bg-gray-400 transition duration-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-blue-600 cursor-pointer text-white px-4 py-2 rounded hover:bg-white hover:text-blue-600 hover:border-1 hover:border-blue-600 transition duration-200"
                  >
                    Upload
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) }
        {showModal === false && folderPathInput && loading && <Uploading/>}
      </div>
    </div>
  );
}

export default Chat;

