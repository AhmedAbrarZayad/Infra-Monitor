import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../shared/colors/colors.dart';
import '../../domain/auth_state.dart';
import '../providers/auth_provider.dart';
import '../widgets/auth_button.dart';
import '../widgets/auth_text_field.dart';

class ResetPasswordPage extends ConsumerStatefulWidget {
  final String email;

  const ResetPasswordPage({super.key, required this.email});

  @override
  ConsumerState<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends ConsumerState<ResetPasswordPage> {
  final _formKey = GlobalKey<FormState>();
  final _otpController = TextEditingController();
  final _passwordController = TextEditingController();
  final _passwordConfirmController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _otpController.dispose();
    _passwordController.dispose();
    _passwordConfirmController.dispose();
    super.dispose();
  }

  void _handleReset() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(authProvider.notifier).resetPassword(
          email: widget.email,
          otp: _otpController.text.trim(),
          newPassword: _passwordController.text,
          newPasswordConfirm: _passwordConfirmController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (prev, next) {
      if (next is AuthUnauthenticated) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Password reset successfully! Please sign in.',
              style: GoogleFonts.roboto(color: Colors.white),
            ),
            backgroundColor: AppColors.success,
          ),
        );
        context.go('/login');
      } else if (next is AuthError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.message),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    });

    final isLoading = authState is AuthLoading;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Icon
                    const Icon(
                      Icons.key_outlined,
                      color: AppColors.warning,
                      size: 64,
                    ),
                    const SizedBox(height: 20),

                    // Title
                    Text(
                      'Reset Password',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Enter the code sent to ${widget.email}',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.roboto(
                        color: AppColors.textSecondary,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // OTP
                    AuthTextField(
                      controller: _otpController,
                      label: 'Reset Code',
                      hint: '000000',
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Enter the code';
                        if (v.trim().length != 6) return 'Code must be 6 digits';
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // New Password
                    AuthTextField(
                      controller: _passwordController,
                      label: 'New Password',
                      hint: '••••••••',
                      obscureText: _obscurePassword,
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                          color: AppColors.textMuted,
                          size: 20,
                        ),
                        onPressed: () =>
                            setState(() => _obscurePassword = !_obscurePassword),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Password is required';
                        if (v.length < 8) return 'At least 8 characters';
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Confirm New Password
                    AuthTextField(
                      controller: _passwordConfirmController,
                      label: 'Confirm New Password',
                      hint: '••••••••',
                      obscureText: _obscureConfirm,
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscureConfirm
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                          color: AppColors.textMuted,
                          size: 20,
                        ),
                        onPressed: () =>
                            setState(() => _obscureConfirm = !_obscureConfirm),
                      ),
                      validator: (v) {
                        if (v != _passwordController.text) return 'Passwords do not match';
                        return null;
                      },
                    ),
                    const SizedBox(height: 28),

                    // Reset Button
                    AuthButton(
                      label: 'Reset Password',
                      isLoading: isLoading,
                      onPressed: isLoading ? null : _handleReset,
                    ),
                    const SizedBox(height: 20),

                    // Back to Login
                    AuthTextButton(
                      label: '← Back to Sign In',
                      onPressed: () => context.go('/login'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
