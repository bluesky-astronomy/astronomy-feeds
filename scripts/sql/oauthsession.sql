begin transaction;
drop table if exists "oauthsession";

create table oauthsession
(
    did                   varchar(255) not null
        primary key,
    handle                varchar(255),
    pds_url               varchar(255) not null,
    authserver_iss        varchar(255) not null,
    access_token          text,
    refresh_token         text,
    dpop_authserver_nonce varchar(255) not null,
    dpop_pds_nonce        varchar(255),
    dpop_private_jwk      varchar(255) not null
);

commit;