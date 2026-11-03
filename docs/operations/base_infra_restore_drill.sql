/*
  P.08.02 restore drill: the newest scheduled FULL backup of base_infra + every LOG backup taken after it, restored
  into a scratch database (base_infra_restore_drill, never over base_infra or base_infra_test); row counts of the
  books compared with base_infra; the scratch database dropped.

      sqlcmd -S . -E -C -b -i docs\operations\base_infra_restore_drill.sql
*/
SET NOCOUNT ON;
USE master;

DECLARE @drill sysname = N'base_infra_restore_drill';
DECLARE @data nvarchar(400) = CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(400));
DECLARE @full nvarchar(400), @full_end datetime, @full_lsn numeric(25, 0);
SELECT TOP 1 @full = m.physical_device_name, @full_end = b.backup_finish_date, @full_lsn = b.last_lsn
FROM msdb.dbo.backupset b JOIN msdb.dbo.backupmediafamily m ON m.media_set_id = b.media_set_id
WHERE b.database_name = N'base_infra' AND b.type = 'D' AND b.is_copy_only = 0
ORDER BY b.backup_finish_date DESC;
IF @full IS NULL THROW 50001, 'no scheduled full backup of base_infra', 1;
PRINT N'full backup: ' + @full + N' (' + CONVERT(nvarchar(30), @full_end, 120) + N')';

IF DB_ID(@drill) IS NOT NULL EXEC (N'ALTER DATABASE [' + @drill + N'] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [' + @drill + N'];');
DECLARE @t0 datetime2 = SYSDATETIME();
DECLARE @mdf nvarchar(400) = @data + N'\base_infra_restore_drill.mdf';
DECLARE @ldf nvarchar(400) = @data + N'\base_infra_restore_drill_log.ldf';
RESTORE DATABASE @drill FROM DISK = @full WITH CHECKSUM, NORECOVERY,
    MOVE N'base_infra' TO @mdf, MOVE N'base_infra_log' TO @ldf;

DECLARE @log nvarchar(400), @n int = 0;
DECLARE logs CURSOR LOCAL FAST_FORWARD FOR
    SELECT m.physical_device_name FROM msdb.dbo.backupset b
    JOIN msdb.dbo.backupmediafamily m ON m.media_set_id = b.media_set_id
    WHERE b.database_name = N'base_infra' AND b.type = 'L' AND b.last_lsn > @full_lsn
    ORDER BY b.backup_finish_date;
OPEN logs;
FETCH NEXT FROM logs INTO @log;
WHILE @@FETCH_STATUS = 0
BEGIN
    RESTORE LOG @drill FROM DISK = @log WITH CHECKSUM, NORECOVERY;
    SET @n += 1;
    FETCH NEXT FROM logs INTO @log;
END
CLOSE logs; DEALLOCATE logs;
RESTORE DATABASE @drill WITH RECOVERY;
PRINT N'restored full + ' + CAST(@n AS nvarchar(10)) + N' log backup(s) in '
    + CAST(DATEDIFF(millisecond, @t0, SYSDATETIME()) AS nvarchar(20)) + N' ms';

SELECT t.name AS table_name,
       (SELECT SUM(p.rows) FROM base_infra.sys.partitions p JOIN base_infra.sys.tables x ON x.object_id = p.object_id
        WHERE x.name = t.name AND p.index_id IN (0, 1)) AS base_infra_rows,
       (SELECT SUM(p.rows) FROM base_infra_restore_drill.sys.partitions p
        JOIN base_infra_restore_drill.sys.tables x ON x.object_id = p.object_id
        WHERE x.name = t.name AND p.index_id IN (0, 1)) AS restored_rows
FROM (VALUES (N'orders'), (N'transactions'), (N'positions'), (N'broker_orders'), (N'broker_executions'),
             (N'trading_discrepancies'), (N'trading_controls'), (N'trading_decisions'), (N'cash_snapshots'),
             (N'factor_values')) AS t(name);

EXEC (N'ALTER DATABASE [' + @drill + N'] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [' + @drill + N'];');
PRINT N'drill database dropped';
