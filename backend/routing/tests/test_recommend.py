from django.test import SimpleTestCase

from routing.services.geo import Checkpoint, sample_checkpoints, segment_miles
from routing.services.recommend import RouteStats, explain, rank_routes


def stats(route_id, severe=0.0, high=0.0, avg=0.0, duration=3600.0, no_travel=0.0):
    return RouteStats(route_id, no_travel, severe, high, avg, duration)


class RankingTests(SimpleTestCase):
    def test_fewest_severe_miles_beats_everything_else(self):
        ranked = rank_routes([
            stats("fast", severe=10, high=0, avg=0.1, duration=1000),
            stats("safe", severe=0, high=90, avg=2.0, duration=9000),
        ])
        self.assertEqual(ranked[0].route_id, "safe")

    def test_high_miles_break_severe_ties(self):
        ranked = rank_routes([stats("a", high=20), stats("b", high=5)])
        self.assertEqual(ranked[0].route_id, "b")

    def test_average_risk_breaks_high_ties(self):
        ranked = rank_routes([stats("a", avg=1.2), stats("b", avg=0.8)])
        self.assertEqual(ranked[0].route_id, "b")

    def test_travel_time_is_last_tiebreaker(self):
        ranked = rank_routes([stats("slow", duration=7200), stats("quick", duration=3600)])
        self.assertEqual(ranked[0].route_id, "quick")

    def test_no_travel_miles_rank_worse_than_severe(self):
        ranked = rank_routes([stats("blocked", no_travel=5), stats("severe", severe=50)])
        self.assertEqual(ranked[0].route_id, "severe")

    def test_explain_names_deciding_criterion(self):
        best, other = stats("a", severe=0), stats("b", severe=12)
        self.assertEqual(explain(best, [other]), "Fewer Severe miles")


class CheckpointTests(SimpleTestCase):
    # ~69 miles of due-north travel (1 degree of latitude).
    PATH = [(40.0, -100.0), (41.0, -100.0)]

    def test_includes_start_and_end(self):
        points = sample_checkpoints(self.PATH, 25)
        self.assertEqual(points[0].mile, 0)
        self.assertAlmostEqual(points[-1].lat, 41.0, places=3)

    def test_spacing_matches_interval(self):
        miles = [p.mile for p in sample_checkpoints(self.PATH, 25)]
        self.assertEqual(miles[:3], [0, 25, 50])

    def test_segment_miles_sum_to_total(self):
        points = sample_checkpoints(self.PATH, 10)
        self.assertAlmostEqual(sum(segment_miles(points)), points[-1].mile, places=6)

    def test_single_checkpoint_owns_no_distance(self):
        self.assertEqual(segment_miles([Checkpoint(0, 0, 0)]), [0.0])
