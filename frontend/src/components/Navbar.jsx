import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <div className="navbar-logo">SE</div>
        <span className="navbar-title">Shared Expenses</span>
      </Link>
      {user && (
        <div className="navbar-user">
          <div className="navbar-avatar">{user.name.charAt(0).toUpperCase()}</div>
          <span className="navbar-name">{user.name}</span>
          <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
