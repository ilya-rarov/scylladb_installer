create table {{ database }}.installations (
  id                 int auto_increment not null primary key,
  start_timestamp    timestamp(6) default current_timestamp(6),
  finish_timestamp   timestamp(6),
  global_status      varchar(50),
  host               varchar(150) not null,
  foreign key (host) references {{ database }}.nodes(host)
);