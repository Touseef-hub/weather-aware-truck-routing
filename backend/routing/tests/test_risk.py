from django.test import SimpleTestCase

from routing.services.risk import Risk, Weather, assess, classify_rain, classify_snow, classify_wind


class ClassifierBoundaryTests(SimpleTestCase):
    def test_wind_boundaries(self):
        cases = {
            0: Risk.LOW, 24.9: Risk.LOW,
            25: Risk.MODERATE, 34.9: Risk.MODERATE,
            35: Risk.HIGH, 44.9: Risk.HIGH,
            45: Risk.SEVERE, 54.9: Risk.SEVERE,
            55: Risk.NO_TRAVEL, 80: Risk.NO_TRAVEL,
        }
        for mph, expected in cases.items():
            with self.subTest(mph=mph):
                self.assertEqual(classify_wind(mph), expected)

    def test_rain_boundaries(self):
        cases = {
            0.09: Risk.LOW, 0.10: Risk.MODERATE, 0.24: Risk.MODERATE,
            0.25: Risk.HIGH, 0.49: Risk.HIGH,
            0.50: Risk.SEVERE, 1.00: Risk.SEVERE,
            1.01: Risk.NO_TRAVEL,
        }
        for value, expected in cases.items():
            with self.subTest(rain=value):
                self.assertEqual(classify_rain(value), expected)

    def test_snow_boundaries(self):
        cases = {
            0.4: Risk.LOW, 0.5: Risk.MODERATE, 0.99: Risk.MODERATE,
            1.0: Risk.HIGH, 1.99: Risk.HIGH,
            2.0: Risk.SEVERE, 3.0: Risk.SEVERE,
            3.01: Risk.NO_TRAVEL,
        }
        for value, expected in cases.items():
            with self.subTest(snow=value):
                self.assertEqual(classify_snow(value), expected)


class LoadRuleTests(SimpleTestCase):
    def test_no_travel_wind_for_any_load(self):
        self.assertEqual(assess(Weather(55, 0, 0), 0).level, Risk.NO_TRAVEL)

    def test_severe_wind_with_heavy_load_is_no_travel(self):
        self.assertEqual(assess(Weather(50, 0, 0), 30_001).level, Risk.NO_TRAVEL)

    def test_severe_wind_at_threshold_load_stays_severe(self):
        self.assertEqual(assess(Weather(50, 0, 0), 30_000).level, Risk.SEVERE)

    def test_high_wind_with_very_heavy_load_is_severe(self):
        result = assess(Weather(40, 0, 0), 40_001)
        self.assertEqual(result.level, Risk.SEVERE)
        self.assertIn("load", result.drivers)

    def test_high_wind_at_threshold_load_stays_high(self):
        self.assertEqual(assess(Weather(40, 0, 0), 40_000).level, Risk.HIGH)

    def test_load_rules_never_lower_risk(self):
        # Heavy rain already makes this Severe; the load rule must not downgrade it.
        self.assertEqual(assess(Weather(36, 0.9, 0), 45_000).level, Risk.SEVERE)

    def test_worst_factor_wins(self):
        result = assess(Weather(10, 0.3, 0.6), 10_000)
        self.assertEqual(result.level, Risk.HIGH)
        self.assertEqual(result.drivers, ("rain",))

    def test_calm_weather_is_low(self):
        self.assertEqual(assess(Weather(5, 0, 0), 80_000).level, Risk.LOW)
