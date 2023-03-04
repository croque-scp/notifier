ALTER TABLE
  manual_sub
ADD INDEX
  manual_sub_thread_post_index
  (thread_id, post_id, user_id);

ALTER TABLE
  thread
ADD INDEX
  thread_category_id_index
  (category_id);

ALTER TABLE
  thread
ADD INDEX
  thread_wiki_id_index
  (wiki_id);