create table {{ database }}.nodes (
  host             varchar(150) not null primary key,
  port             varchar(10) not null,
  username         varchar(100) not null,
  password         varchar(150),
  db_version       varchar(10) not null,
  cluster_name     varchar(100) not null,
  seed_node        varchar(150) not null,
  os_version       varchar(100)
);