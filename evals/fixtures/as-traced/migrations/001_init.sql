CREATE TABLE tenants (
  id            bigserial PRIMARY KEY,
  name          text NOT NULL,
  plan          text NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'team', 'business')),
  seats         integer NOT NULL DEFAULT 3,
  billing_email text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id            bigserial PRIMARY KEY,
  tenant_id     bigint REFERENCES tenants (id),          -- NULL for staff (support, admin)
  email         text NOT NULL UNIQUE,
  display_name  text NOT NULL DEFAULT '',
  role          text NOT NULL CHECK (role IN ('owner', 'member', 'support', 'admin')),
  password_hash text NOT NULL,
  preferences   jsonb NOT NULL DEFAULT '{}'::jsonb,
  disabled      boolean NOT NULL DEFAULT false,
  last_login_at timestamptz
);

CREATE TABLE projects (
  id         bigserial PRIMARY KEY,
  tenant_id  bigint NOT NULL REFERENCES tenants (id),
  name       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
  id             bigserial PRIMARY KEY,
  tenant_id      bigint NOT NULL REFERENCES tenants (id),
  project_id     bigint NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  title          text NOT NULL,
  status         text NOT NULL CHECK (status IN ('todo', 'doing', 'done')),
  due_date       date,
  assignee_email text
);

CREATE TABLE files (
  id           bigserial PRIMARY KEY,
  project_id   bigint NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  name         text NOT NULL,
  storage_key  text NOT NULL UNIQUE,
  content_type text NOT NULL,
  size         integer NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ON projects (tenant_id);
CREATE INDEX ON tasks (project_id);
CREATE INDEX ON files (project_id);
