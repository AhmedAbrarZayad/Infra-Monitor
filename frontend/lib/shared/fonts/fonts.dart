import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central text styles for the app.
class AppFonts {
  AppFonts._();

  /// Returns a text theme backed by Google Fonts.
  static TextTheme textTheme([Color? textColor]) {
    final color = textColor ?? Colors.white;
    return TextTheme(
      titleLarge: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      bodyMedium: GoogleFonts.roboto(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: color,
      ),
      bodySmall: GoogleFonts.roboto(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: color,
      ),
      displayLarge: GoogleFonts.inter(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: color,
      ),
    );
  }
}
