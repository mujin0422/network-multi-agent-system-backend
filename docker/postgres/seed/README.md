# Additional GNS3 benchmark scenarios (development seed)

This expansion adds **17 GNS3/MPLS-core scenarios** to the original 10 cases,
without changing the database schema or the original seed records.

**Source:** Fault families are analogous to general troubleshooting taxonomies
(including NIKA), but these are independently authored scenarios for this
project's Cisco IOS GNS3 lab. They are **not** imported NIKA cases or NIKA
evaluation results. The baseline lab reference is
[`docs/device-configure.txt`](../../../docs/device-configure.txt).

| Fault family | Scenario keys | Cases |
|---|---|---:|
| Core / CE link shutdown | `pe1-fa1-0-core-link-down`, `pe2-fa1-0-core-link-down`, `ce-1b-fa0-0-uplink-down`, `ce-2a-fa0-0-uplink-down` | 4 |
| Layer-2 uplink/trunk shutdown | `switch1-fa1-0-trunk-down`, `switch3-fa1-0-trunk-down` | 2 |
| OSPF backbone config | `pe1-ospf-network-missing`, `pe2-ospf-network-missing`, `p2-ospf-backbone-area-mismatch` | 3 |
| MPLS forwarding | `pe1-fa2-0-mpls-disabled`, `pe2-fa2-0-mpls-disabled`, `p1-fa1-0-mpls-disabled` | 3 |
| IPv4 addressing | `ce-1b-uplink-wrong-ip`, `ce-2b-uplink-wrong-ip` | 2 |
| Traffic policy / ACL | `pe1-cus-b-acl-102-block`, `pe2-cus-a-acl-103-block` | 2 |
| Loopback administration | `p1-loopback0-admin-down` | 1 |
| **Total** | | **17** |

Each scenario contains `preconditions`, `injection`,
`fault_verification`, `ground_truth`, `evaluation_required_terms`,
and a cleanup plan intended to restore the **reference configuration**.
The evaluator remains rule-based; these cases do not improve semantic RCA
scoring by themselves.

## Apply safely

**Fresh Docker DB volume:** the read-only SQL file is mounted at
`/docker-entrypoint-initdb.d/03_benchmark_expansion.sql` and runs once after
the base seed during PostgreSQL initialization.

**Existing database:** run migrations first, then use SQL input redirection
(the migration runner intentionally does not own development seed data):

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < docker/postgres/seed/03_benchmark_expansion.sql
```

The insert uses `ON CONFLICT (scenario_key) DO NOTHING`; reapplying it
preserves scenario changes made through the UI. This only inserts database
records. It does **not** inject network faults at seed time.

Check the resulting sample set with:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT scenario_key, name FROM benchmark_scenarios ORDER BY scenario_key"'
```

## Preconditions and risks

- Confirm the actual GNS3 topology and device port names match the reference.
  In particular, switch uplinks must be connected and **up**, otherwise their
  preconditions should fail without applying a fault.
- Each scenario should run **alone** on an otherwise healthy lab. Do not
  overlap benchmark runs on the same router or link.
- Run Cleanup and verify network recovery manually after each test. The
  generated cleanup only restores known reference values, not an arbitrary
  original configuration.
- IP replacement scenarios deliberately use incorrect uplink addresses
  (`192.168.22.2` or `192.168.44.2`). Restore the previous addresses after
  testing.
- ACL cases assume ACL **102** and **103** are not already present. The
  preconditions check the global ACL and interface attachment; do not run if
  the ACL numbers are used for other purposes.
- Some older seed cases refer to P3 interfaces or default routes not configured
  in the checked-in reference. These remain untouched; their suitability
  depends on your current lab state.
- Cisco images, IOS versions, topology links, and actual CLI output can
  differ. These are *candidate executable scenarios*, **not** cases confirmed
  by a live GNS3 end-to-end run in this change.

Unsupported families such as BGP neighbor changes, VRF leaks, VLAN tagging,
MTU manipulation, DHCP/DNS faults, and congestion **were intentionally not
seeded** because the current typed `BenchmarkAction` and network command
builder do not implement safe injection/cleanup for those mechanisms.
