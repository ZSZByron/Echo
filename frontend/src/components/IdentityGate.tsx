import { useState, useEffect } from 'react';
import { registerUser, type IdentityInfo } from '../api/identity';

export interface IdentityGateProps {
  children: React.ReactNode;
}

const USER_ID_KEY = 'user_id';

export function IdentityGate({ children }: IdentityGateProps) {
  const [userId, setUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check localStorage first
    const storedUserId = localStorage.getItem(USER_ID_KEY);

    if (storedUserId) {
      setUserId(storedUserId);
      setIsLoading(false);
    } else {
      // Register new user
      registerUser()
        .then((info: IdentityInfo) => {
          localStorage.setItem(USER_ID_KEY, info.user_id);
          setUserId(info.user_id);
          setIsLoading(false);
        })
        .catch((err) => {
          setError(err.message || 'Failed to register');
          setIsLoading(false);
        });
    }
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Registering your identity...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="bg-red-950/50 border border-red-700 rounded-lg p-6 max-w-md">
          <h2 className="text-red-400 text-lg font-semibold mb-2">Registration Error</h2>
          <p className="text-red-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* ID Badge Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-white">
              <span className="text-slate-400 text-sm mr-2">User ID:</span>
              <span className="font-mono">{userId}</span>
            </div>
            <span className="px-3 py-1 bg-green-900/50 text-green-300 border border-green-700/50 rounded-full text-xs font-medium">
              FREE
            </span>
          </div>
        </div>
      </div>

      {/* Child content */}
      {children}
    </div>
  );
}
