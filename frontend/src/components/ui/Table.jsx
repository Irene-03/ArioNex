import EmptyState from './EmptyState';

export default function Table({
  columns,
  rows,
  rowKey = 'id',
  loading = false,
  emptyTitle = 'داده‌ای یافت نشد',
  emptyDesc = 'هنوز رکوردی ثبت نشده است.',
  emptyIcon,
  onRowClick,
  ...rest
}) {
  return (
    <div className="ax-table-wrap" {...rest}>
      <table className="ax-table">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} style={col.width ? { width: col.width } : undefined}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        {!loading && rows.length > 0 && (
          <tbody>
            {rows.map((row, i) => (
              <tr key={row[rowKey] ?? i} onClick={onRowClick ? () => onRowClick(row) : undefined} style={onRowClick ? { cursor: 'pointer' } : undefined}>
                {columns.map(col => (
                  <td key={col.key}>{col.render ? col.render(row) : row[col.key]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        )}
      </table>
      {loading && (
        <div style={{ padding: '18px 16px' }}>
          {[0, 1, 2].map(i => (
            <div key={i} className="ax-skeleton ax-skeleton--text" style={{ height: 34, marginBottom: 10 }} />
          ))}
        </div>
      )}
      {!loading && rows.length === 0 && <EmptyState title={emptyTitle} desc={emptyDesc} icon={emptyIcon} />}
    </div>
  );
}
