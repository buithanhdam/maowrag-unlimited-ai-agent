'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Database, Bot, Settings,Users, Brain } from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

export default function Navbar() {
  const pathname = usePathname();
  
  const navItems: NavItem[] = [
    {
      path: '/chat',
      label: 'Chat',
      icon: <MessageSquare className="w-5 h-5" />,
    },
    {
      path: '/kb',
      label: 'Knowledge Base',
      icon: <Database className="w-5 h-5" />,
    },
    {
      path: '/communication',
      label: 'Communication',
      icon: <Users className="w-5 h-5" />,
    },
    {
      path: '/agent',
      label: 'Agent',
      icon: <Bot className="w-5 h-5" />,
    },
    {
      path: '/llm',
      label: 'LLM',
      icon: <Brain className="w-5 h-5" />,
    },
    {
      path: '/settings',
      label: 'Settings',
      icon: <Settings className="w-5 h-5" />,
    },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 fixed w-full top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <span className="font-bold text-xl">AI LLM System</span>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                const isActive = pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    href={item.path}
                    className={`${
                      isActive
                        ? 'border-blue-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium gap-2`}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}