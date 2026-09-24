-- Run once in Supabase → SQL Editor.

create table if not exists notes (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  chat_id bigint,
  telegram_message_id bigint,
  source text check (source in ('voice', 'text')),
  transcript text not null,
  score int check (score between 0 and 10),
  score_reason text,
  angle text,
  status text not null default 'received'   -- received | rejected | drafting | drafted
);

create table if not exists drafts (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  note_id uuid references notes(id),
  chat_id bigint,
  body text not null,
  model text,
  news_headline text,
  news_source text,
  news_date text,
  news_url text,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  decided_at timestamptz,
  telegram_message_ids bigint[] default '{}'
);
create index if not exists drafts_msg_idx on drafts using gin (telegram_message_ids);

create table if not exists voice_skill (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  content text not null,
  active boolean not null default true
);

-- Dedupe Telegram retries.
create table if not exists processed_updates (
  update_id bigint primary key,
  created_at timestamptz not null default now()
);

-- Rejected notes and drafts are kept, never deleted. Lock tables to the service key only.
alter table notes enable row level security;
alter table drafts enable row level security;
alter table voice_skill enable row level security;
alter table processed_updates enable row level security;
