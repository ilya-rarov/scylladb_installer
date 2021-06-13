select
{{ columns }}
from nodes 
{{ join_installations }} join installations on nodes.host = installations.host
{{ join_statuses}} join statuses on installations.id = statuses.istallation_id
where {{ filter }};