queries = {
    "enable_foreign_keys": "PRAGMA foreign_keys = ON",
    "create_tables_script": """
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id TEXT NOT NULL PRIMARY KEY,
            username TEXT NOT NULL,
            frequency TEXT NOT NULL,
            language TEXT NOT NULL
        );
        CREATE TABLE manual_subs (
            user_id TEXT NOT NULL PRIMARY KEY
                REFERENCES user_configs (user_id),
            thread_id TEXT NOT NULL,
            post_id TEXT,
            sub INTEGER NOT NULL CHECK (sub IN (-1, 1)),
            UNIQUE (user_id, thread_id, post_id, sub)
        );
        CREATE TABLE IF NOT EXISTS wikis (
            id TEXT NOT NULL PRIMARY KEY,
            secure INTEGER NOT NULL CHECK (secure IN (0, 1))
        );
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT NOT NULL PRIMARY KEY,
            title TEXT NOT NULL,
            wiki_id TEXT NOT NULL REFERENCES wikis (id)
        );
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT NOT NULL PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES threads (id),
            parent_post_id TEXT REFERENCES posts (id),
            posted_timestamp INTEGER NOT NULL,
            title TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL
        );
    """,
    "get_posts_in_subscribed_threads": """
        SELECT
            posts.title, posts.username, posts.posted_timestamp,
            threads.title,
            wikis.id, wikis.secure
        FROM
            posts
            LEFT JOIN
            threads ON posts.thread_id = threads.id
            LEFT JOIN
            wikis ON threads.wiki_id = wikis.id
        WHERE
            (
                -- Get posts in threads subscribed to
                threads.id IN (
                    SELECT thread_id FROM manual_subs
                    WHERE user_id = :user_id AND sub=1
                )
                -- Get posts in threads started by the user
                OR threads.id IN (
                    SELECT thread_id FROM posts
                    GROUP BY thread_id
                    HAVING MIN(posted_timestamp) AND user_id = :user_id
                )
            )
            -- Remove posts in threads unsubscribed from
            AND threads.id NOT IN (
                SELECT thread_id FROM manual_subs
                WHERE user_id = :user_id AND sub = -1
            )
            -- Remove posts not posted in the last time period
            AND posts.posted_timestamp >= :search_timestamp
            -- Remove posts made by the user
            AND posts.user_id <> :user_id
            -- Remove posts the already responded to
            AND posts.id NOT IN (
                SELECT parent_post_id FROM posts WHERE user_id = :user_id
            )
    """,
    "get_replies_to_subscribed_posts": """
        SELECT
            posts.title, posts.username, posts.posted_timestamp,
            parent_posts.title, parent_posts.posted_timestamp,
            threads.title,
            wikis.id, wikis.secure
        FROM
            posts
            LEFT JOIN
            threads ON posts.thread_id = threads.id
            LEFT JOIN
            wikis ON threads.wiki_id = wikis.id
            LEFT JOIN
            posts AS parent_posts ON posts.parent_post_id = parent_posts.id
        WHERE
            (
                -- Get replies to posts subscribed to
                parent_posts.id IN (
                    SELECT post_id FROM manual_subs
                    WHERE user_id = :user_id AND sub=1
                )
                -- Get replies to posts made by the user
                OR parent_posts.user_id = :user_id
            )
            -- Remove replies to posts unsubscribed from
            AND parent_posts.id NOT IN (
                SELECT post_id FROM manual_subs
                WHERE user_id = :user_id AND sub = -1
            )
            -- Remove posts not posted in the last time period
            AND posts.posted_timestamp >= :search_timestamp
            -- Remove posts made by the user
            AND posts.user_id <> :user_id
            -- Remove posts the user already responded to
            AND posts.id NOT IN (
                SELECT parent_post_id FROM posts WHERE user_id = :user_id
            )
    """,
}
