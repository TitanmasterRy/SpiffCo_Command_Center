import { useMemo, useState } from 'react';
import { Card } from '../Card';
import { StatusBadge, type StatusKind } from '../StatusBadge';
import { ApiError } from '../../api/http';
import {
  useApproveUser,
  useAuthCatalog,
  useDeleteUser,
  useUpdateUser,
  useUsers,
} from '../../hooks/useAuth';
import type { AuthCatalog, PermissionInfo, Role, UserSummary } from '../../types/auth';

const ROLES: Role[] = ['viewer', 'operator', 'admin'];

function statusBadge(status: string): { kind: StatusKind; label: string } {
  if (status === 'active') return { kind: 'ok', label: 'Active' };
  if (status === 'pending') return { kind: 'warn', label: 'Pending' };
  return { kind: 'error', label: 'Disabled' };
}

/** One editable user row: role, per-permission checkboxes, and status actions. */
function UserRow({ user, catalog }: { user: UserSummary; catalog: AuthCatalog }) {
  const approve = useApproveUser();
  const update = useUpdateUser();
  const remove = useDeleteUser();

  const [role, setRole] = useState<Role>((user.role as Role) ?? 'viewer');
  const [perms, setPerms] = useState<Set<string>>(new Set(user.permissions));

  const busy = approve.isPending || update.isPending || remove.isPending;
  const error = approve.error ?? update.error ?? remove.error;
  const badge = statusBadge(user.status);

  const togglePerm = (key: string) => {
    setPerms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Selecting a role pre-fills the permission set from that role's preset.
  const applyRole = (next: Role) => {
    setRole(next);
    setPerms(new Set(catalog.roles[next] ?? []));
  };

  const permissionList = [...perms];

  if (user.is_superuser) {
    return (
      <div className="rounded-md border border-surface-border p-3">
        <div className="flex items-center justify-between">
          <span className="font-medium text-slate-100">{user.username}</span>
          <StatusBadge kind="ok" label="Owner" />
        </div>
        <p className="mt-1 text-xs text-slate-500">
          The owner account has full access and is managed via backend configuration.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-md border border-surface-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-100">{user.username}</span>
          <StatusBadge kind={badge.kind} label={badge.label} />
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          Role
          <select
            value={role}
            onChange={(e) => applyRole(e.target.value as Role)}
            className="rounded-md border border-surface-border bg-surface px-2 py-1 text-sm text-slate-100"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3">
        {catalog.permissions.map((perm: PermissionInfo) => (
          <label
            key={perm.key}
            className="flex items-center gap-2 text-xs text-slate-300"
            title={perm.key}
          >
            <input
              type="checkbox"
              checked={perms.has(perm.key)}
              onChange={() => togglePerm(perm.key)}
              className="accent-accent"
            />
            {perm.label}
          </label>
        ))}
      </fieldset>

      <div className="flex flex-wrap items-center gap-2">
        {user.status === 'pending' ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => approve.mutate({ id: user.id, role, permissions: permissionList })}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Approve
          </button>
        ) : (
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              update.mutate({ id: user.id, patch: { role, permissions: permissionList } })
            }
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Save changes
          </button>
        )}

        {user.status === 'active' && (
          <button
            type="button"
            disabled={busy}
            onClick={() => update.mutate({ id: user.id, patch: { status: 'disabled' } })}
            className="rounded-md border border-surface-border px-3 py-1.5 text-sm text-slate-300 hover:bg-surface-overlay disabled:opacity-50"
          >
            Disable
          </button>
        )}
        {user.status === 'disabled' && (
          <button
            type="button"
            disabled={busy}
            onClick={() => update.mutate({ id: user.id, patch: { status: 'active' } })}
            className="rounded-md border border-surface-border px-3 py-1.5 text-sm text-slate-300 hover:bg-surface-overlay disabled:opacity-50"
          >
            Enable
          </button>
        )}

        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (confirm(`Delete account "${user.username}"? This cannot be undone.`)) {
              remove.mutate(user.id);
            }
          }}
          className="rounded-md border border-status-error/40 px-3 py-1.5 text-sm text-status-error hover:bg-status-error/10 disabled:opacity-50"
        >
          {user.status === 'pending' ? 'Reject' : 'Delete'}
        </button>

        {error && (
          <span className="text-xs text-status-error">
            {error instanceof ApiError ? error.message : 'Action failed.'}
          </span>
        )}
      </div>
    </div>
  );
}

/** Account management: approve pending sign-ups and set per-user permissions. */
export function UsersPanel() {
  const { data: users, isLoading, error } = useUsers(true);
  const { data: catalog } = useAuthCatalog(true);

  const pending = useMemo(
    () => (users ?? []).filter((u) => u.status === 'pending'),
    [users],
  );
  const others = useMemo(
    () => (users ?? []).filter((u) => u.status !== 'pending'),
    [users],
  );

  if (error) {
    return (
      <Card title="Accounts">
        <p className="text-sm text-status-error">
          {error instanceof ApiError ? error.message : 'Failed to load users.'}
        </p>
      </Card>
    );
  }
  if (isLoading || !catalog) {
    return <p className="text-sm text-slate-500">Loading accounts…</p>;
  }

  return (
    <div className="space-y-4">
      <Card title={`Pending approval (${pending.length})`}>
        {pending.length === 0 ? (
          <p className="text-sm text-slate-500">No account requests waiting.</p>
        ) : (
          <div className="space-y-3">
            {pending.map((u) => (
              <UserRow key={u.id} user={u} catalog={catalog} />
            ))}
          </div>
        )}
      </Card>

      <Card title="Accounts">
        <div className="space-y-3">
          {others.map((u) => (
            <UserRow key={u.id} user={u} catalog={catalog} />
          ))}
        </div>
      </Card>
    </div>
  );
}
