create table {{ database }}.statuses (
  status_name         varchar(50) not null,
  status_timestamp    timestamp(6) not null default current_timestamp(6),
  installation_id     int not null,
  foreign key (installation_id) references {{ database }}.installations(id)
);
