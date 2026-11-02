# Proposal: move seat inventory to MongoDB (backend team)

Postgres won't scale for the relaunch. We propose moving `seat` and `seat_hold` to a sharded MongoDB
cluster, sharded by `event_id`, and keeping Redis in front of it as the source of seat availability.
MongoDB scales horizontally, so on-sales will never be a problem again. We have not benchmarked the
current database at relaunch volumes.
