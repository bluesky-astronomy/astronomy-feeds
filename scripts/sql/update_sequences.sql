SELECT setval(pg_get_serial_sequence('account', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   account;


SELECT setval(pg_get_serial_sequence('botactions', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   botactions;


SELECT setval(pg_get_serial_sequence('activitylog', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   activitylog;


SELECT setval(pg_get_serial_sequence('modactions', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   modactions;


SELECT setval(pg_get_serial_sequence('post', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   post;


SELECT setval(pg_get_serial_sequence('subscriptionstate', 'id')
            , COALESCE(max(id) + 1, 1)
            , false)
FROM   subscriptionstate;

COMMIT;