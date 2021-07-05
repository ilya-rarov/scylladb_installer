select
{{ columns }}
from nodes 
{{ join_installations }} join installations on nodes.host = installations.host
{{ join_statuses}} join statuses on installations.id = statuses.installation_id
where {{ filter }};