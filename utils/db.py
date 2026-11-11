def closeConnection(conn, *cursors):
    for cur in cursors:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()