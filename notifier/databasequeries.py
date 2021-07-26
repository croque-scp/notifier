queries = {
    "enable_foreign_keys": "PRAGMA foreign_keys = ON",
    "create_tables_script": """
        CREATE TABLE IF NOT EXISTS user_config (
            user_id TEXT NOT NULL PRIMARY KEY,
            username TEXT NOT NULL,
            frequency TEXT NOT NULL,
            language TEXT NOT NULL
        );
        CREATE TABLE manual_sub (
            user_id TEXT NOT NULL REFERENCES user_config (user_id),
            thread_id TEXT NOT NULL,
            post_id TEXT,
            sub INTEGER NOT NULL CHECK (sub IN (-1, 1)),
            UNIQUE (user_id, thread_id, post_id, sub)
        );
        CREATE TABLE IF NOT EXISTS wiki (
            id TEXT NOT NULL PRIMARY KEY,
            secure INTEGER NOT NULL CHECK (secure IN (0, 1))
        );
        CREATE TABLE IF NOT EXISTS thread (
            id TEXT NOT NULL PRIMARY KEY,
            title TEXT NOT NULL,
            wiki_id TEXT NOT NULL REFERENCES wiki (id)
        );
        CREATE TABLE IF NOT EXISTS post (
            id TEXT NOT NULL PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES thread (id),
            parent_post_id TEXT REFERENCES post (id),
            posted_timestamp INTEGER NOT NULL,
            title TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL
        );
    """,
    "get_posts_in_subscribed_threads": """
        SELECT
            post.id AS id,
            post.title AS title,
            post.username AS username,
            post.posted_timestamp AS posted_timestamp,
            thread.id AS thread_id,
            thread.title AS thread_title,
            wiki.id AS wiki_id,
            wiki.secure AS wiki_secure
        FROM
            post
            LEFT JOIN
            thread ON post.thread_id = thread.id
            LEFT JOIN
            wiki ON thread.wiki_id = wiki.id
        WHERE
            (
                -- Get posts in threads subscribed to
                EXISTS (
                    SELECT NULL FROM
                        manual_sub
                    WHERE
                        manual_sub.user_id = :user_id
                        AND manual_sub.thread_id = thread.id
                        AND manual_sub.post_id IS NULL
                        AND manual_sub.sub = 1
                )

                -- Get posts in threads started by the user
                OR EXISTS (
                    SELECT NULL FROM
                        post AS first_post
                    GROUP BY
                        first_post.thread_id
                    HAVING
                        MIN(first_post.posted_timestamp)
                        AND first_post.user_id = :user_id
                        AND first_post.thread_id = post.thread_id
                )
            )

            -- Remove posts in threads unsubscribed from
            AND NOT EXISTS (
                SELECT NULL FROM
                    manual_sub
                WHERE
                    manual_sub.user_id = :user_id
                    AND manual_sub.thread_id = thread.id
                    AND manual_sub.post_id IS NULL
                    AND manual_sub.sub = -1
            )

            -- Remove posts not posted in the last time period
            AND post.posted_timestamp >= :search_timestamp

            -- Remove posts made by the user
            AND post.user_id <> :user_id

            -- Remove posts the user already responded to
            AND NOT EXISTS (
                SELECT NULL FROM
                    post AS child_post
                WHERE
                    child_post.parent_post_id = post.id
                    AND child_post.user_id = :user_id
            )
    """,
    "get_replies_to_subscribed_posts": """
        SELECT
            post.id AS id,
            post.title AS title,
            post.username AS username,
            post.posted_timestamp AS posted_timestamp,
            parent_post.id AS parent_post_id,
            parent_post.title AS parent_title,
            parent_post.posted_timestamp AS parent_posted_timestamp,
            thread.id AS thread_id,
            thread.title AS thread_title,
            wiki.id AS wiki_id,
            wiki.secure AS wiki_secure
        FROM
            post
            LEFT JOIN
            thread ON post.thread_id = thread.id
            LEFT JOIN
            wiki ON thread.wiki_id = wiki.id
            LEFT JOIN
            post AS parent_post ON post.parent_post_id = parent_post.id
        WHERE
            (
                -- Get replies to posts subscribed to
                EXISTS (
                    SELECT NULL FROM
                        manual_sub
                    WHERE
                        manual_sub.post_id = parent_post.id
                        AND manual_sub.thread_id = thread.id
                        AND manual_sub.user_id = :user_id
                        AND manual_sub.sub = 1
                )

                -- Get replies to posts made by the user
                OR parent_post.user_id = :user_id
            )

            -- Remove replies to posts unsubscribed from
            AND NOT EXISTS (
                SELECT NULL FROM
                    manual_sub
                WHERE
                    manual_sub.post_id = parent_post.id
                    AND manual_sub.thread_id = thread.id
                    AND manual_sub.user_id = :user_id
                    AND manual_sub.sub = -1
            )

            -- Remove posts not posted in the last time period
            AND post.posted_timestamp >= :search_timestamp

            -- Remove posts made by the user
            AND post.user_id <> :user_id

            -- Remove posts the user already responded to
            AND NOT EXISTS (
                SELECT NULL FROM
                    post AS child_post
                WHERE
                    child_post.parent_post_id = post.id
                    AND child_post.user_id = :user_id
            )
    """,
}
