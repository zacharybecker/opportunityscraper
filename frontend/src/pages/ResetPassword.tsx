import { Center, Card, PasswordInput, Button, Title, Stack, Alert, Text, Anchor } from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconCheck, IconAlertCircle } from '@tabler/icons-react'
import { useMutation } from '@tanstack/react-query'
import { useSearchParams, Link } from 'react-router-dom'
import apiClient from '../api/client'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const form = useForm({
    initialValues: { new_password: '', confirmPassword: '' },
    validate: {
      new_password: (v) => (v.length >= 8 ? null : 'Password must be at least 8 characters'),
      confirmPassword: (v, values) => (v === values.new_password ? null : 'Passwords do not match'),
    },
  })

  const mutation = useMutation({
    mutationFn: (values: { new_password: string }) =>
      apiClient.post('/auth/reset-password', { token, new_password: values.new_password }).then((r) => r.data),
  })

  return (
    <Center h="100vh" bg="gray.1">
      <Card shadow="md" p="xl" w={400}>
        <Stack>
          <Title order={2} ta="center">Set New Password</Title>
          {mutation.isSuccess && (
            <Alert icon={<IconCheck size={16} />} color="green" title="Password Reset">
              Your password has been reset. <Anchor component={Link} to="/login">Login now</Anchor>
            </Alert>
          )}
          {mutation.isError && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
              {(mutation.error as any)?.response?.data?.detail || 'Invalid or expired reset token'}
            </Alert>
          )}
          {!mutation.isSuccess && (
            <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
              <Stack>
                <PasswordInput label="New Password" placeholder="At least 8 characters" {...form.getInputProps('new_password')} />
                <PasswordInput label="Confirm Password" placeholder="Repeat password" {...form.getInputProps('confirmPassword')} />
                <Button type="submit" fullWidth loading={mutation.isPending}>
                  Reset Password
                </Button>
              </Stack>
            </form>
          )}
          <Text size="sm" ta="center">
            <Anchor component={Link} to="/login">Back to Login</Anchor>
          </Text>
        </Stack>
      </Card>
    </Center>
  )
}
