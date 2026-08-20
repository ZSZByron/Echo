import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IdentityGate } from '../IdentityGate';
import '@testing-library/jest-dom/vitest';

// Mock the identity API
vi.mock('../../api/identity', () => ({
  registerUser: vi.fn(),
}));

import * as identityModule from '../../api/identity';

describe('IdentityGate', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    vi.mocked(identityModule.registerUser).mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<IdentityGate>Protected Content</IdentityGate>);

    expect(screen.getByText('Registering your identity...')).toBeInTheDocument();
  });

  it('displays user ID and FREE badge after registration', async () => {
    vi.mocked(identityModule.registerUser).mockResolvedValue({
      user_id: 'u_abc123def456',
      tier: 'FREE',
    });

    render(<IdentityGate>Protected Content</IdentityGate>);

    await waitFor(() => {
      expect(screen.getByText('u_abc123def456')).toBeInTheDocument();
      expect(screen.getByText('FREE')).toBeInTheDocument();
    });
  });

  it('uses existing user_id from localStorage', async () => {
    localStorage.setItem('user_id', 'u_existing789');
    vi.mocked(identityModule.registerUser).mockResolvedValue({
      user_id: 'u_new123',
      tier: 'FREE',
    });

    render(<IdentityGate>Protected Content</IdentityGate>);

    await waitFor(() => {
      expect(screen.getByText('u_existing789')).toBeInTheDocument();
      expect(identityModule.registerUser).not.toHaveBeenCalled();
    });
  });

  it('stores user_id in localStorage after registration', async () => {
    vi.mocked(identityModule.registerUser).mockResolvedValue({
      user_id: 'u_newuser123',
      tier: 'FREE',
    });

    render(<IdentityGate>Protected Content</IdentityGate>);

    await waitFor(() => {
      expect(localStorage.getItem('user_id')).toBe('u_newuser123');
    });
  });

  it('shows error message when registration fails', async () => {
    vi.mocked(identityModule.registerUser).mockRejectedValue(new Error('Network error'));

    render(<IdentityGate>Protected Content</IdentityGate>);

    await waitFor(() => {
      expect(screen.getByText('Registration Error')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('renders children after successful registration', async () => {
    vi.mocked(identityModule.registerUser).mockResolvedValue({
      user_id: 'u_abc123',
      tier: 'FREE',
    });

    render(<IdentityGate>Protected Content</IdentityGate>);

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });
});
