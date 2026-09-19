import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Mic, Package, Clock, Settings } from 'lucide-react';

export default function Navigation() {
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/assistant', icon: Mic, label: 'Voice' },
    { path: '/inventory', icon: Package, label: 'Inventory' },
    { path: '/history', icon: Clock, label: 'History' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-200 z-50 md:relative md:border-t-0 md:border-b md:shadow-sm">
      <div className="flex justify-around items-center h-16 max-w-screen-xl mx-auto md:justify-start md:gap-8 md:px-6">
        {/* Mobile & Desktop Nav Links */}
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-full h-full space-y-1 text-xs font-medium transition-colors md:flex-row md:w-auto md:space-y-0 md:gap-2 md:text-sm ${
                isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
              }`
            }
          >
            <item.icon className="w-5 h-5 md:w-4 md:h-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}