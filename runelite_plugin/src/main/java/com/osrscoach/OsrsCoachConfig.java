package com.osrscoach;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;

@ConfigGroup("osrscoach")
public interface OsrsCoachConfig extends Config
{
    @ConfigItem(
        keyName = "showPlan",
        name = "Show plan",
        description = "Show the top 3 plan steps"
    )
    default boolean showPlan()
    {
        return true;
    }

    @ConfigItem(
        keyName = "showRatings",
        name = "Show ratings",
        description = "Show ratings summary"
    )
    default boolean showRatings()
    {
        return true;
    }

    @ConfigItem(
        keyName = "showBlockers",
        name = "Show blockers",
        description = "Show top blockers"
    )
    default boolean showBlockers()
    {
        return true;
    }
}
