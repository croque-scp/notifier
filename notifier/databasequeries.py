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
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT NOT NULL PRIMARY KEY,
            title TEXT NOT NULL,
            wiki TEXT NOT NULL -- Needed to construct URL
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
    # TODO Post responses need wiki, thread id, post id
    # TODO Posts or threads need wiki stored somehow
    # Wiki can be returned via JOIN?
    # Possibly join post<-thread<-wiki? Might make querying easier
    "get_posts_in_subscribed_threads": """
        SELECT
            title, username, posted_timestamp
        FROM
            posts
        WHERE
            (
                -- Get posts in threads subscribed to
                thread_id IN (
                    SELECT thread_id FROM manual_subs
                    WHERE user_id=:user_id AND sub=1
                )
                -- Get posts in threads started by the user
                OR thread_id IN (
                    SELECT id FROM threads WHERE id IN (
                        SELECT thread_id FROM posts
                        GROUP BY thread_id
                        HAVING MIN(posted_timestamp) AND user_id=:user_id
                    )
                )
            )
            -- Remove posts in threads unsubscribed from
            AND thread_id NOT IN (
                SELECT thread_id FROM manual_subs
                WHERE user_id=:user_id AND sub=-1
            )
            -- Remove posts already responded to
            AND parent_post_id NOT IN (
                SELECT id FROM posts WHERE user_id=:user_id
            )
            -- Remove posts not posted in the last time period
            AND NOT posted_timestamp<:search_timestamp
            -- Remove posts made by the user
            AND NOT user_id=:user_id
    """,
    "get_replies_to_subscribed_posts": """
        SELECT
            title, username, posted_datetime
        FROM
            posts
        WHERE
            (
                -- Get replies to posts subscribed to
                id IN (
                    SELECT post_id FROM manual_subs
                    WHERE user_id=:user_id AND sub=1
                )
                -- Get replies to posts made by the user
                OR parent_post_id IN (
                    SELECT id FROM posts
                    WHERE user_id=:user_id
                )
            )
            -- Remove replies to posts unsubscribed from
            AND id NOT IN (
                SELECT post_id FROM manual_subs
                WHERE user_id=:user_id AND sub=-1
            )
            -- Remove posts already responded to
            AND parent_post_id NOT IN (
                SELECT id FROM posts WHERE user_id=:user_id
            )
            -- Remove posts not posted in the last time period
            AND NOT posted_datetime<:search_datetime
            -- Remove posts made by the user
            AND NOT user_id=:user_id
    """,
}
