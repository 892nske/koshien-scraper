-- =====================================================================
-- マスタデータ(地区・都道府県・ラウンド・夏の地方大会)
--
-- seed.sql ではなくマイグレーションに置く。これらは外部キーの参照先であり、
-- 本番環境でも必ず存在しなければならない参照データだから。
-- supabase/seed.sql はローカルの `supabase db reset` でしか実行されない。
-- =====================================================================


insert into regions (name, sort_order) values
  ('北海道',1),('東北',2),('関東',3),('東京',4),('北信越',5),
  ('東海',6),('近畿',7),('中国',8),('四国',9),('九州',10)
on conflict (name) do nothing;

insert into prefectures (id, name, region_id) values
  ( 1,'北海道',(select id from regions where name='北海道')),
  ( 2,'青森',  (select id from regions where name='東北')),
  ( 3,'岩手',  (select id from regions where name='東北')),
  ( 4,'宮城',  (select id from regions where name='東北')),
  ( 5,'秋田',  (select id from regions where name='東北')),
  ( 6,'山形',  (select id from regions where name='東北')),
  ( 7,'福島',  (select id from regions where name='東北')),
  ( 8,'茨城',  (select id from regions where name='関東')),
  ( 9,'栃木',  (select id from regions where name='関東')),
  (10,'群馬',  (select id from regions where name='関東')),
  (11,'埼玉',  (select id from regions where name='関東')),
  (12,'千葉',  (select id from regions where name='関東')),
  (13,'東京',  (select id from regions where name='東京')),
  (14,'神奈川',(select id from regions where name='関東')),
  (15,'新潟',  (select id from regions where name='北信越')),
  (16,'富山',  (select id from regions where name='北信越')),
  (17,'石川',  (select id from regions where name='北信越')),
  (18,'福井',  (select id from regions where name='北信越')),
  (19,'山梨',  (select id from regions where name='関東')),
  (20,'長野',  (select id from regions where name='北信越')),
  (21,'岐阜',  (select id from regions where name='東海')),
  (22,'静岡',  (select id from regions where name='東海')),
  (23,'愛知',  (select id from regions where name='東海')),
  (24,'三重',  (select id from regions where name='東海')),
  (25,'滋賀',  (select id from regions where name='近畿')),
  (26,'京都',  (select id from regions where name='近畿')),
  (27,'大阪',  (select id from regions where name='近畿')),
  (28,'兵庫',  (select id from regions where name='近畿')),
  (29,'奈良',  (select id from regions where name='近畿')),
  (30,'和歌山',(select id from regions where name='近畿')),
  (31,'鳥取',  (select id from regions where name='中国')),
  (32,'島根',  (select id from regions where name='中国')),
  (33,'岡山',  (select id from regions where name='中国')),
  (34,'広島',  (select id from regions where name='中国')),
  (35,'山口',  (select id from regions where name='中国')),
  (36,'徳島',  (select id from regions where name='四国')),
  (37,'香川',  (select id from regions where name='四国')),
  (38,'愛媛',  (select id from regions where name='四国')),
  (39,'高知',  (select id from regions where name='四国')),
  (40,'福岡',  (select id from regions where name='九州')),
  (41,'佐賀',  (select id from regions where name='九州')),
  (42,'長崎',  (select id from regions where name='九州')),
  (43,'熊本',  (select id from regions where name='九州')),
  (44,'大分',  (select id from regions where name='九州')),
  (45,'宮崎',  (select id from regions where name='九州')),
  (46,'鹿児島',(select id from regions where name='九州')),
  (47,'沖縄',  (select id from regions where name='九州'))
on conflict (id) do nothing;

insert into rounds (code, label, sort_order) values
  ('r1','1回戦',1),('r2','2回戦',2),('r3','3回戦',3),
  ('qf','準々決勝',4),('sf','準決勝',5),('f','決勝',6)
on conflict (code) do nothing;

-- 夏の地方大会:通常年の49代表
insert into summer_qualifiers (name, prefecture_id, note)
select '北北海道', 1, '北海道の北半分' union all
select '南北海道', 1, '北海道の南半分' union all
select '東東京', 13, '東京の東半分' union all
select '西東京', 13, '東京の西半分'
on conflict (name) do nothing;

insert into summer_qualifiers (name, prefecture_id)
select p.name, p.id
from prefectures p
where p.id not in (1, 13)   -- 北海道・東京は分割済み
on conflict (name) do nothing;

-- 記念大会の分割枠(必要年のみ使用)
insert into summer_qualifiers (name, prefecture_id, note) values
  ('北大阪', 27, '記念大会の分割枠'),
  ('南大阪', 27, '記念大会の分割枠'),
  ('北埼玉', 11, '記念大会の分割枠'),
  ('南埼玉', 11, '記念大会の分割枠'),
  ('東千葉', 12, '記念大会の分割枠'),
  ('西千葉', 12, '記念大会の分割枠'),
  ('北神奈川', 14, '記念大会の分割枠'),
  ('南神奈川', 14, '記念大会の分割枠'),
  ('東愛知', 23, '記念大会の分割枠'),
  ('西愛知', 23, '記念大会の分割枠'),
  ('東兵庫', 28, '記念大会の分割枠'),
  ('西兵庫', 28, '記念大会の分割枠'),
  ('北福岡', 40, '記念大会の分割枠'),
  ('南福岡', 40, '記念大会の分割枠')
on conflict (name) do nothing;

