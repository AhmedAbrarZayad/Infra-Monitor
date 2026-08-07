import 'package:flutter/material.dart';

/// Central color palette for the app. Keep colors here so theme and widgets
/// can reference the same values.
class AppColors {
	AppColors._();

	// Primary branding
	static const Color primary = Color(0xFF2E6AFF); // vivid blue
	static const Color primaryVariant = Color(0xFF1D4ED8);

	// Secondary / accent
	static const Color secondary = Color(0xFF6D5EFF); // violet accent
	static const Color secondaryVariant = Color(0xFF7C3AED);

	// Background / surfaces (dark-first palette)
	static const Color background = Color(0xFF071428);
	static const Color surface = Color(0xFF0F1724);
	static const Color card = Color(0xFF0E1520);

	// Text colors
	static const Color textPrimary = Color(0xFFF8FAFC);
	static const Color textSecondary = Color(0xFF9AA4B2);
	static const Color textMuted = Color(0xFF6B7280);

	// Semantic colors
	static const Color success = Color(0xFF20C997);
	static const Color warning = Color(0xFFF59E0B);
	static const Color danger = Color(0xFFEF4444);
	static const Color info = Color(0xFF60A5FA);

	// Borders, dividers
	static const Color border = Color(0xFF1E293B);

	// Misc
	static const Color liveIndicator = Color(0xFF10B981);
}
