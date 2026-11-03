# base_infra backups

`base_infra` holds the books: positions, cash, the order ledger, executions, decisions, controls and
discrepancies. Since 2026-11-03 it is backed up on a schedule (task P.08.02 in `LIVE_TRADING_READINESS.txt`).
The schedule and retention below are the owner's choice.

| What | When | Kept | Where |
|---|---|---|---|
| Full backup, compressed, with checksum, then verified | daily 02:00 | 14 days | `...\MSSQL\Backup\base_infra_scheduled\base_infra_FULL_<yyyyMMdd_HHmm>.bak` |
| Transaction-log backup, compressed, with checksum | every hour from 00:30 | 14 days | `...\base_infra_scheduled\base_infra_LOG_<yyyyMMdd_HHmm>.trn` |

- **Database:** recovery model FULL. You lose at most one hour of books.
- **Files:** they stay on this machine (`C:`). This protects against mistakes and corruption, not against losing
  the disk or the machine.
- **Manual backups:** the COPY_ONLY backups taken before a schema change stay in the `Backup` folder itself. The
  14-day cleanup only looks in `base_infra_scheduled`, so it never deletes them.

## One-time setup: start SQL Server Agent (administrator)

The two jobs run only while the **SQL Server Agent** service runs. It was stopped, with a manual start type, and
changing that needs an administrator prompt (right-click PowerShell, then *Run as administrator*):

```powershell
Set-Service SQLSERVERAGENT -StartupType Automatic
Start-Service SQLSERVERAGENT
```

To check it (no admin needed):

```powershell
Get-Service SQLSERVERAGENT          # Status: Running, StartType: Automatic
```

## Jobs

Defined in `docs/operations/base_infra_backup_jobs.sql`; applying it again re-creates them:

```
sqlcmd -S . -E -C -b -i docs\operations\base_infra_backup_jobs.sql
```

The two jobs are:
- `base_infra - full backup (daily 02:00)`
- `base_infra - log backup (hourly)`

## Monitoring

- **`ops status`** prints the last scheduled full and log backup, and a `BACKUP ALERT:` line when one is missing or
  stale (full older than 26 h, log older than 2 h).
- **A running STM live session** pushes the same alert to the phone through ntfy (P.08.01).

## Restore drill

The script is `docs/operations/base_infra_restore_drill.sql`. It restores the newest scheduled full backup and every
log backup taken after it into a scratch database, `base_infra_restore_drill` (never over `base_infra` or
`base_infra_test`). It then compares the row counts of the books with `base_infra` and drops the scratch database.

```
sqlcmd -S . -E -C -b -W -i docs\operations\base_infra_restore_drill.sql
```

First drill, 2026-11-03 12:31:
- Restored full backup `base_infra_FULL_20261103_1230.bak` plus one log backup in 1.1 s.
- Every row count matched `base_infra`:

  | Table | Rows |
  |---|---|
  | orders | 15,556 |
  | transactions | 15,568 |
  | positions | 185 |
  | broker_orders | 628 |
  | broker_executions | 679 |
  | trading_discrepancies | 42 |
  | trading_controls | 2 |
  | trading_decisions | 30 |
  | cash_snapshots | 1 |
  | factor_values | 688,496 |

## Restoring base_infra for real

1. Stop every session and the dashboard (nothing may write to `base_infra`).
2. Take a tail-log backup if the database is still readable:
   `BACKUP LOG [base_infra] TO DISK = N'...\base_infra_TAIL.trn' WITH NORECOVERY, CHECKSUM`.
3. Restore in this order:
   1. the newest full backup, `WITH NORECOVERY`;
   2. every later `.trn` in time order, `WITH NORECOVERY`;
   3. the tail log, `WITH RECOVERY`.

   The drill script shows the exact statements.
4. Run `ops status` and a `check()` start (STM RUNBOOK §1). Recovery compares the books with IBKR before any order.
