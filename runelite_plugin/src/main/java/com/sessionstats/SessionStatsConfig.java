package com.sessionstats;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;

@ConfigGroup("sessionstats")
public interface SessionStatsConfig extends Config
{
    @ConfigItem(
        keyName = "exportInterval",
        name = "Export Interval",
        description = "How often to export stats (in game ticks)"
    )
    default int exportInterval()
    {
        return 2;
    }
}
