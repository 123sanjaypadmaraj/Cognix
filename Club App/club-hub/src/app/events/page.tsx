import { createClient } from "@/lib/supabase/server";
import { EventCard, type EventCardData } from "@/components/EventCard";
import { Empty, PageHeader } from "@/components/ui";

export const metadata = { title: "Events" };

export default async function EventsPage() {
  const supabase = await createClient();
  const now = new Date().toISOString();
  const select = "id, title, category, venue, starts_at, clubs(name, slug, accent_color)";
  const [{ data: up }, { data: past }] = await Promise.all([
    supabase.from("events").select(select).eq("status", "published").gte("starts_at", now).order("starts_at").limit(60),
    supabase.from("events").select(select).eq("status", "published").lt("starts_at", now).order("starts_at", { ascending: false }).limit(24),
  ]);
  const upcoming = (up ?? []) as unknown as EventCardData[];
  const earlier = (past ?? []) as unknown as EventCardData[];

  return (
    <>
      <PageHeader title="Events" subtitle="Everything happening across all clubs." />
      <h2 className="mb-3 text-lg font-semibold">Upcoming</h2>
      {upcoming.length === 0 ? (
        <Empty>No upcoming events.</Empty>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{upcoming.map((e) => <EventCard key={e.id} e={e} />)}</div>
      )}
      <h2 className="mb-3 mt-10 text-lg font-semibold">Recent</h2>
      {earlier.length === 0 ? (
        <Empty>No past events yet.</Empty>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{earlier.map((e) => <EventCard key={e.id} e={e} />)}</div>
      )}
    </>
  );
}
