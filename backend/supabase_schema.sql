-- Supabase schema for RakshaAI
-- Run this in the Supabase SQL editor.

create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamp with time zone default now()
);

create table tracking_sessions (
  id uuid primary key default gen_random_uuid(),
  user_name text not null,
  permission text,
  started_at timestamp with time zone default now(),
  ended_at timestamp with time zone,
  status text default 'ONLINE'
);

create table location_points (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references tracking_sessions(id),
  user_name text not null,
  lat double precision not null,
  lng double precision not null,
  speed double precision,
  accuracy double precision,
  battery text,
  vehicle text,
  risk_score int default 0,
  risk_band text default 'SAFE',
  created_at timestamp with time zone default now()
);

create table sos_alerts (
  id uuid primary key default gen_random_uuid(),
  user_name text not null,
  session_id uuid references tracking_sessions(id),
  message text,
  latitude double precision,
  longitude double precision,
  created_at timestamp with time zone default now()
);

create table trusted_contacts (
  id uuid primary key default gen_random_uuid(),
  user_name text not null,
  contact_name text not null,
  contact_phone text,
  contact_email text,
  created_at timestamp with time zone default now()
);
