-- Table for users --
 CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student'
        CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Table for maintenance_teams --
CREATE TABLE maintenance_teams(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL UNIQUE CHECK (
        category IN (
            'Plumbing',
            'Electrical',
            'HVAC',
            'Structural',
            'General Maintenance',
            'IT / Network'
        )
    ),
    email TEXT
);

-- Rows for maintenance_teams --
INSERT INTO maintenance_teams (team_name, category)
VALUES
('Campus Plumbing and Waterworks Crew', 'Plumbing'),
('Facilities Electrical and Power Techs', 'Electrical'),
('Climate Control and Ventilation Specialists', 'HVAC'),
('Campus Facilities Engineering', 'Structural'),
('General Facilities Handyman', 'General Maintenance'),
('Campus IT Infrastructure Support', 'IT / Network');

-- Table for work_orders --
create table public.work_orders (
  id uuid not null default gen_random_uuid (),
  title text not null,
  issue_description text not null,
  building text not null,
  room text null,
  category text not null,
  severity text not null,
  assigned_team_id uuid null,
  repair_steps text null,
  image_url text null,
  ai_confidence numeric(4, 3) null,
  status text not null default 'Open'::text,
  latitude double precision null,
  longitude double precision null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  priority text null default 'Medium'::text,
  report_count integer null default 1,
  email_status text null,
  email_sent_at timestamp with time zone null,
  location_status text null default 'Unknown'::text,
  image_path text null,
  constraint work_orders_pkey primary key (id),
  constraint work_orders_assigned_team_id_fkey foreign KEY (assigned_team_id) references maintenance_teams (id),
  constraint work_orders_check check (
    (
      (
        (latitude is null)
        and (longitude is null)
      )
      or (
        (
          (latitude >= ('-90'::integer)::double precision)
          and (latitude <= (90)::double precision)
        )
        and (
          (longitude >= ('-180'::integer)::double precision)
          and (longitude <= (180)::double precision)
        )
      )
    )
  ),
  constraint work_orders_priority_check check (
    (
      priority = any (
        array[
          'Low'::text,
          'Medium'::text,
          'High'::text,
          'Critical'::text
        ]
      )
    )
  ),
  constraint work_orders_severity_check check (
    (
      severity = any (
        array[
          'Critical'::text,
          'High'::text,
          'Medium'::text,
          'Low'::text
        ]
      )
    )
  ),
  constraint work_orders_ai_confidence_check check (
    (
      (ai_confidence >= (0)::numeric)
      and (ai_confidence <= (1)::numeric)
    )
  ),
  constraint work_orders_status_check check (
    (
      status = any (
        array[
          'Open'::text,
          'In Progress'::text,
          'Completed'::text,
          'Cancelled'::text
        ]
      )
    )
  ),
  constraint work_orders_category_check check (
    (
      category = any (
        array[
          'Plumbing'::text,
          'Electrical'::text,
          'HVAC'::text,
          'Structural'::text,
          'General Maintenance'::text,
          'IT / Network'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

-- Table for student_reports --
CREATE TABLE student_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    work_order_id UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    issue_description TEXT NOT NULL,
    image_url TEXT,
    building TEXT NOT NULL,
    room TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE (student_id, work_order_id));

-- Table for map_coordinates --
CREATE TABLE map_coordinates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name TEXT UNIQUE NOT NULL,
    polygon_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Rows in map_coordinates --
INSERT INTO map_coordinates (feature_name, polygon_data) VALUES
('Tower A', '{"type": "Polygon", "coordinates": [[[101.7007787, 3.0554425], [101.7004654, 3.0551654], [101.7003116, 3.0553201], [101.7006249, 3.0555972], [101.7007787, 3.0554425]]]}'),
('Tower C', '{"type": "Polygon", "coordinates": [[[101.7007508, 3.0557817], [101.7005773, 3.0559928], [101.7001717, 3.0556457], [101.7003452, 3.0554347], [101.7007508, 3.0557817]]]}'),
('Tower D', '{"type": "Polygon", "coordinates": [[[101.6998067, 3.0555378], [101.6993784, 3.0551372], [101.6992123, 3.0553063], [101.6996624, 3.0556941], [101.6998067, 3.0555378]]]}'),
('Tower E', '{"type": "Polygon", "coordinates": [[[101.6995526, 3.0557896], [101.6991203, 3.0552553], [101.6989459, 3.055335], [101.6992822, 3.055932], [101.6995526, 3.0557896]]]}'),
('Tower S', '{"type": "Polygon", "coordinates": [[[101.7006519, 3.0560294], [101.7001262, 3.0556549], [101.6998532, 3.0560089], [101.6994317, 3.0561776], [101.6998358, 3.0568564], [101.7002759, 3.0566249], [101.7000443, 3.0562391], [101.7001938, 3.0560452], [101.7004395, 3.0562817], [101.7006519, 3.0560294]]]}'),
('Dorm', '{"type": "Polygon", "coordinates": [[[101.6997769, 3.0567971], [101.6994161, 3.0561434], [101.6992666, 3.0562035], [101.6996303, 3.0568609], [101.6997769, 3.0567971]]]}'),
('Dorm 2', '{"type": "Polygon", "coordinates": [[[101.6993361, 3.0559914], [101.699082, 3.0555639], [101.6989627, 3.0556248], [101.6991932, 3.0560525], [101.6993361, 3.0559914]]]}'),
('Dorm 3', '{"type": "Polygon", "coordinates": [[[101.6991275, 3.0560905], [101.6989628, 3.055796], [101.6988456, 3.0558907], [101.6989895, 3.0561891], [101.6991275, 3.0560905]]]}'),
('Dorm 4', '{"type": "Polygon", "coordinates": [[[101.6994657, 3.0567377], [101.6992339, 3.056246], [101.6990489, 3.0563449], [101.69929, 3.0568177], [101.6994657, 3.0567377]]]}'),
('The whole school', '{"type": "Polygon", "coordinates": [[[101.7008529, 3.0550055], [101.6991752, 3.0548473], [101.6984122, 3.0565801], [101.7006608, 3.0571855], [101.7008529, 3.0550055]]]}'),
('Tower B', '{"type": "Polygon", "coordinates": [[[101.7000565, 3.0552553], [101.69979, 3.0549638], [101.699518, 3.0551822], [101.6998493, 3.0554845], [101.7000565, 3.0552553]]]}');
