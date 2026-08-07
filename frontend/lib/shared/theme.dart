import 'package:flutter/material.dart';
import 'colors/colors.dart';
import 'fonts/fonts.dart';

class AppTheme {
  AppTheme._();

  static final ThemeData theme = ThemeData.dark().copyWith(
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      surface: AppColors.surface,
    ),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
    ),
    cardColor: AppColors.card,
    dividerColor: AppColors.border,
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: AppColors.surface,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textSecondary,
      showUnselectedLabels: true,
    ),
    textTheme: AppFonts.textTheme(AppColors.textPrimary),
  );
}
