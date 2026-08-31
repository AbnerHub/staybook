import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/rooms", label: "Rooms" },
  { to: "/guests", label: "Guests" },
  { to: "/reservations", label: "Reservations" },
  { to: "/availability", label: "Availability" },
  { to: "/history", label: "History" },
];

function linkClassName({ isActive }) {
  return isActive ? "sidebar__link sidebar__link--active" : "sidebar__link";
}

export default function Sidebar() {
  return (
    <nav className="admin-layout__sidebar" aria-label="Navegación principal">
      <ul className="sidebar__list">
        {NAV_ITEMS.map(({ to, label }) => (
          <li key={to} className="sidebar__item">
            <NavLink to={to} className={linkClassName}>
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
