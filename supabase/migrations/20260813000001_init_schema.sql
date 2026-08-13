-- =====================================================================
-- 甲子園(春の選抜 / 夏の選手権)データベース スキーマ
-- PostgreSQL 15+ / Supabase
-- =====================================================================

create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------
-- 0. 型
-- ---------------------------------------------------------------------
do $$ begin
  create type season_type as enum ('spring', 'summer');
exception when duplicate_object then null; end $$;

do $$ begin
  create type game_status as enum ('final', 'draw', 'forfeit', 'no_game', 'scheduled');
exception when duplicate_object then null; end $$;

-- 共通: updated_at 自動更新
create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end $$ language plpgsql;

-- ---------------------------------------------------------------------
-- 1. 地区(春夏共通)
-- ---------------------------------------------------------------------
create table regions (
  id          smallint generated always as identity primary key,
  name        text     not null unique,
  sort_order  smallint not null
);
comment on table regions is '地区。春夏共通。全代表校が必ずいずれかに属する';

-- ---------------------------------------------------------------------
-- 2. 都道府県
-- ---------------------------------------------------------------------
create table prefectures (
  id         smallint primary key,                    -- JISコード 1-47
  name       text     not null unique,                -- 「長野」「滋賀」(接尾辞なし)
  region_id  smallint not null references regions(id)
);
create index on prefectures (region_id);

-- ---------------------------------------------------------------------
-- 3. 夏の地方大会(代表枠)  ※夏のみ
-- ---------------------------------------------------------------------
create table summer_qualifiers (
  id            smallint generated always as identity primary key,
  name          text     not null unique,             -- 北北海道 / 西東京 / 南大阪 / 宮城 …
  prefecture_id smallint references prefectures(id),  -- 複数県にまたがる旧大会は null
  note          text
);
create index on summer_qualifiers (prefecture_id);
comment on table summer_qualifiers is '夏の地方大会。春の出場行では使用しない';

-- ---------------------------------------------------------------------
-- 4. 学校
-- ---------------------------------------------------------------------
create table schools (
  id            integer generated always as identity primary key,
  name          text     not null,                    -- 現校名
  kana          text,
  prefecture_id smallint not null references prefectures(id),
  is_active     boolean  not null default true,
  note          text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (name, prefecture_id)
);
create index on schools (prefecture_id);
create index schools_name_trgm_idx on schools using gin (name gin_trgm_ops);
create trigger schools_updated_at before update on schools
  for each row execute function set_updated_at();

-- 校名の別名・旧称(スクレイピング名寄せ用)
create table school_aliases (
  id        integer generated always as identity primary key,
  school_id integer not null references schools(id) on delete cascade,
  alias     text    not null,
  kind      text    not null default 'notation'
              check (kind in ('former_name', 'notation', 'source_label')),
  unique (school_id, alias)
);
create index school_aliases_alias_trgm_idx on school_aliases using gin (alias gin_trgm_ops);

-- ---------------------------------------------------------------------
-- 5. 大会
-- ---------------------------------------------------------------------
create table tournaments (
  id          smallint    generated always as identity primary key,
  year        smallint    not null check (year between 1915 and 2100),
  season      season_type not null,
  edition     smallint,
  is_memorial boolean     not null default false,
  team_count  smallint,
  note        text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (year, season),
  unique (id, season)          -- entries の複合FK用
);
create trigger tournaments_updated_at before update on tournaments
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------
-- 6. 出場(大会 × 学校)
-- ---------------------------------------------------------------------
create table entries (
  id                  integer     generated always as identity primary key,
  tournament_id       smallint    not null references tournaments(id) on delete cascade,
  season              season_type not null,
  school_id           integer     not null references schools(id),
  name_at_time        text        not null,
  prefecture_id       smallint    not null references prefectures(id),
  region_id           smallint    not null references regions(id),
  summer_qualifier_id smallint    references summer_qualifiers(id),
  is_21st_century     boolean     not null default false,
  selection_note      text,
  appearance_no       smallint,
  consecutive_no      smallint,
  source_url          text,
  scraped_at          timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  unique (tournament_id, school_id),
  unique (id, tournament_id),   -- games の複合FK用

  -- season が親大会と一致することを保証
  foreign key (tournament_id, season) references tournaments (id, season),

  -- 夏は地方大会が必須、春は必ず null
  constraint entries_qualifier_by_season_ck check (
    (season = 'summer' and summer_qualifier_id is not null) or
    (season = 'spring' and summer_qualifier_id is null)
  ),
  -- 21世紀枠は春のみ
  constraint entries_21c_spring_only_ck check (
    season = 'spring' or is_21st_century = false
  )
);
create index on entries (school_id);
create index on entries (prefecture_id);
create index on entries (region_id);
create index on entries (summer_qualifier_id);
-- 1つの地方大会からの代表は1校
create unique index entries_one_rep_per_qualifier_uq
  on entries (tournament_id, summer_qualifier_id)
  where summer_qualifier_id is not null;
create trigger entries_updated_at before update on entries
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------
-- 7. ラウンド
-- ---------------------------------------------------------------------
create table rounds (
  code       text primary key,
  label      text not null,
  sort_order smallint not null unique
);

-- ---------------------------------------------------------------------
-- 8. 試合
-- ---------------------------------------------------------------------
-- 【設計変更】当初は 先攻/後攻 を必須としていたが、取得元(Wikipedia)が保持するのは
-- 「勝利校・敗戦校・スコア」であり打順は原則不明。そのため以下の構成に変更した。
--   entry1_id / entry2_id … 掲載順の2校(確定試合では entry1 = 勝利校)
--   first_bat_entry_id    … 先攻が判明した場合のみ(サヨナラ勝ちなら勝者が後攻と確定)
create table games (
  id                  integer     generated always as identity primary key,
  tournament_id       smallint    not null references tournaments(id) on delete cascade,
  round_code          text        not null references rounds(code),
  day_no              smallint,
  game_no             smallint,
  game_date           date,
  entry1_id           integer     not null references entries(id),
  entry2_id           integer     not null references entries(id),
  score1              smallint,
  score2              smallint,
  innings             smallint,
  winner_entry_id     integer     references entries(id),
  first_bat_entry_id  integer     references entries(id),             -- 判明時のみ
  is_walkoff          boolean     not null default false,             -- サヨナラ
  status              game_status not null default 'final',
  replay_seq          smallint    not null default 0,                 -- 0=初戦, 1=再試合
  replay_of_game_id   integer     references games(id),
  note                text,
  source_url          text,
  scraped_at          timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  -- 対戦カードの向き(掲載順)に依存しない一意キーを作るための正規化列
  pair_lo integer generated always as
    (case when entry1_id < entry2_id then entry1_id else entry2_id end) stored,
  pair_hi integer generated always as
    (case when entry1_id < entry2_id then entry2_id else entry1_id end) stored,

  constraint games_distinct_teams_ck check (entry1_id <> entry2_id),
  constraint games_winner_is_participant_ck check (
    winner_entry_id is null or winner_entry_id in (entry1_id, entry2_id)
  ),
  constraint games_first_bat_is_participant_ck check (
    first_bat_entry_id is null or first_bat_entry_id in (entry1_id, entry2_id)
  ),
  -- 勝者を持つのは final(確定)と forfeit(不戦勝=進出校が勝者)。
  -- draw / no_game / scheduled は勝者なし。
  constraint games_status_winner_ck check (
    (status in ('final', 'forfeit')     and winner_entry_id is not null) or
    (status not in ('final', 'forfeit') and winner_entry_id is null)
  ),
  constraint games_draw_score_ck check (
    status <> 'draw' or score1 is null or score2 is null or score1 = score2
  ),
  -- 不戦勝(辞退)は試合が行われずスコアを持たない。
  constraint games_forfeit_no_score_ck check (
    status <> 'forfeit' or (score1 is null and score2 is null)
  ),
  unique (tournament_id, round_code, pair_lo, pair_hi, replay_seq),

  -- 両チームが同一大会の出場校であることを保証
  foreign key (entry1_id, tournament_id) references entries (id, tournament_id),
  foreign key (entry2_id, tournament_id) references entries (id, tournament_id)
);
create index on games (tournament_id);
create index on games (entry1_id);
create index on games (entry2_id);
create index on games (winner_entry_id);
create index on games (game_date);
create trigger games_updated_at before update on games
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------
-- 9. ビュー
-- ---------------------------------------------------------------------

-- 9.1 1試合 → 2行(チーム視点)
create or replace view v_game_teams as
with sides as (
  select g.id as game_id, g.tournament_id, g.round_code, g.game_date, g.innings,
         g.status, g.winner_entry_id, g.replay_seq, g.is_walkoff,
         g.entry1_id as entry_id,
         g.entry2_id as opponent_entry_id,
         g.score1    as runs_for,
         g.score2    as runs_against,
         case when g.first_bat_entry_id is null then null
              else g.first_bat_entry_id = g.entry1_id end as is_first_bat
  from games g
  union all
  select g.id, g.tournament_id, g.round_code, g.game_date, g.innings,
         g.status, g.winner_entry_id, g.replay_seq, g.is_walkoff,
         g.entry2_id,
         g.entry1_id,
         g.score2,
         g.score1,
         case when g.first_bat_entry_id is null then null
              else g.first_bat_entry_id = g.entry2_id end
  from games g
)
select
  s.game_id,
  s.tournament_id,
  t.year,
  t.season,
  s.round_code,
  r.label      as round_label,
  r.sort_order as round_order,
  s.game_date,
  s.innings,
  s.status,
  s.replay_seq,
  s.is_walkoff,
  s.is_first_bat,
  -- 自チーム
  s.entry_id,
  e.school_id,
  e.name_at_time,
  e.prefecture_id,
  e.region_id,
  e.summer_qualifier_id,
  e.is_21st_century,
  -- 相手チーム
  s.opponent_entry_id,
  o.school_id           as opponent_school_id,
  o.name_at_time        as opponent_name_at_time,
  o.prefecture_id       as opponent_prefecture_id,
  o.region_id           as opponent_region_id,
  o.summer_qualifier_id as opponent_summer_qualifier_id,
  -- 結果
  s.runs_for,
  s.runs_against,
  case
    when s.status = 'draw' then 'draw'
    when s.status = 'scheduled' then null
    when s.winner_entry_id = s.entry_id then 'win'
    else 'loss'
  end as result
from sides s
join entries     e on e.id = s.entry_id
join entries     o on o.id = s.opponent_entry_id
join tournaments t on t.id = s.tournament_id
join rounds      r on r.code = s.round_code;

-- 9.2 出場の平坦ビュー
create or replace view v_entries_full as
select e.id as entry_id, t.year, t.season, t.edition, t.is_memorial,
       e.school_id, s.name as school_name, e.name_at_time,
       p.name as prefecture_name, rg.name as region_name,
       q.name as summer_qualifier_name,
       e.is_21st_century, e.selection_note, e.appearance_no, e.consecutive_no
from entries e
join tournaments t on t.id = e.tournament_id
join schools     s on s.id = e.school_id
join prefectures p on p.id = e.prefecture_id
join regions     rg on rg.id = e.region_id
left join summer_qualifiers q on q.id = e.summer_qualifier_id;

-- ---------------------------------------------------------------------
-- 10. RLS(Supabase: 読み取りのみ公開。書き込みは service_role)
-- ---------------------------------------------------------------------
alter table regions            enable row level security;
alter table prefectures        enable row level security;
alter table summer_qualifiers  enable row level security;
alter table schools            enable row level security;
alter table school_aliases     enable row level security;
alter table tournaments        enable row level security;
alter table entries            enable row level security;
alter table rounds             enable row level security;
alter table games              enable row level security;

do $$
declare tbl text;
begin
  foreach tbl in array array['regions','prefectures','summer_qualifiers','schools',
                             'school_aliases','tournaments','entries','rounds','games']
  loop
    execute format(
      'create policy %I_public_read on %I for select to anon, authenticated using (true)',
      tbl, tbl);
  end loop;
end $$;

