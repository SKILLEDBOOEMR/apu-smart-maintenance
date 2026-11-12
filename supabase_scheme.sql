
-- 1. Users Table
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  auth_user_id uuid NOT NULL,
  email text NOT NULL,
  full_name text NOT NULL,
  role text NOT NULL DEFAULT 'student'::text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

-- 2. Maintenance Teams Table
CREATE TABLE public.maintenance_teams (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  team_name text NOT NULL,
  category text NOT NULL,
  email text,
  CONSTRAINT maintenance_teams_pkey PRIMARY KEY (id)
);

-- 3. Work Orders Table
CREATE TABLE public.work_orders (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL,
  issue_description text NOT NULL,
  building text NOT NULL,
  room text,
  category text NOT NULL,
  severity text NOT NULL,
  assigned_team_id uuid,
  repair_steps text,
  image_url text,
  ai_confidence numeric,
  status text NOT NULL DEFAULT 'Open'::text,
  latitude double precision,
  longitude double precision,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  priority text DEFAULT 'Medium'::text,
  report_count integer DEFAULT 1,
  email_status text,
  email_sent_at timestamp with time zone,
  location_status text DEFAULT 'Unknown'::text,
  image_path text,
  floor smallint,
  CONSTRAINT work_orders_pkey PRIMARY KEY (id),
  CONSTRAINT fk_assigned_team FOREIGN KEY (assigned_team_id) REFERENCES public.maintenance_teams (id)
);

-- 4. Student Reports Table
CREATE TABLE public.student_reports (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  work_order_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT student_reports_pkey PRIMARY KEY (id),
  CONSTRAINT fk_student FOREIGN KEY (student_id) REFERENCES public.users (id),
  CONSTRAINT fk_work_order FOREIGN KEY (work_order_id) REFERENCES public.work_orders (id)
);

-- 5. Map Coordinates Table
CREATE TABLE public.map_coordinates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  feature_name text NOT NULL,
  polygon_data jsonb NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  floor_min smallint,
  floor_max smallint,
  CONSTRAINT map_coordinates_pkey PRIMARY KEY (id)
);
