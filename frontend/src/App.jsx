import './App.css';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import NotFoundPage from './pages/NotFoundPage';
import Chat from './pages/Chat';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
// import { Toaster } from 'react-hot-toast';

function App() {
  return (
    <Router>
      <Routes>
        {/* <Toaster position="top-right" /> */}
        <Route path="*" element={<NotFoundPage />} />
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/chat" element={<Chat />} />
      </Routes>
    </Router>
  );
}

export default App;
