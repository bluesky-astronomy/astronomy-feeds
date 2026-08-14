begin transaction;
drop table if exists "oauthrequest";

create table oauthrequest
(
    state                 varchar(255) not null
        primary key,
    authserver_iss        varchar(255) not null,
    did                   varchar(255),
    handle                varchar(255),
    pds_url               varchar(255),
    pkce_verifier         varchar(255) not null,
    scope                 varchar(255) not null,
    dpop_authserver_nonce varchar(255) not null,
    dpop_private_jwk      varchar(255) not null
);

commit;