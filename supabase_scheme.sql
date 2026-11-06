-- Table for work_orders --
CREATE TABLE work_orders (
    id SERIAL PRIMARY KEY, -- Unique auto-incrementing ID number for each work order ticket
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL, -- Timestamp of when the work order was created
    issue_description TEXT NOT NULL, -- Detailed text description of the reported maintenance issue
    building TEXT NOT NULL, -- The name of the building or zone (e.g., 'Tower A', 'The whole school')
    room TEXT NOT NULL, -- Specific room or area identifier within the building
    category TEXT, -- Categorized type of issue (eg. plumbing, electrical, carpentry)
    severity TEXT, -- Severity or priority level of the maintenance request
    repair_steps TEXT, -- Recommended or generated steps required to fix the issue
    image_url TEXT, -- Public storage URL pointing to the uploaded photo of the issue
    status TEXT DEFAULT 'Open' NOT NULL, -- Current progress status of the repair (defaults to 'Open' until resolved)
    latitude DOUBLE PRECISION, -- Geographic latitude coordinate for the issue location
    longitude DOUBLE PRECISION -- Geographic longitude coordinate for the issue location
);

-- Table for map_coordinates --
CREATE TABLE map_coordinates (
    id SERIAL PRIMARY KEY, -- Work order ticket
    feature_name TEXT, -- The name of the building or zone (e.g., 'Tower A', 'The whole school')
    polygon_data JSONB NOT NULL, -- Stores the full polygon type and coordinate array as a JSON object
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL -- Automatically generates and stores the timestamp when the record is created
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
