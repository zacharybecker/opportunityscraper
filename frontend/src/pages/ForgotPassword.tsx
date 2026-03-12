import { Center, Card, TextInput, Button, Title, Stack, Alert, Text, Anchor } from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconCheck, IconAlertCircle } from '@tabler/icons-react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'

export default function ForgotPassword() {
  const form = useForm({
    initialValues: { email: '' },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : 'Invalid email'),
    },
  })

  const mutation = useMutation({
    mutationFn: (values: { email: string }) =>
      apiClient.post('/auth/forgot-password', values).then((r) => r.data),
  })

  return (
    <Center h="100vh" bg="gray.1">
      <Card shadow="md" p="xl" w={400}>
        <Stack>
          <Title order={2} ta="center">Reset Password</Title>
          {mutation.isSuccess && (
            <Alert icon={<IconCheck size={16} />} color="green" title="Check your email">
              If an account exists with that email, a reset link has been sent.
            </Alert>
          )}
          {mutation.isError && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
              Something went wrong. Please try again.
            </Alert>
          )}
          <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
            <Stack>
              <TextInput label="Email" placeholder="your@email.com" {...form.getInputProps('email')} />
              <Button type="submit" fullWidth loading={mutation.isPending}>
                Send Reset Link
              </Button>
            </Stack>
          </form>
          <Text size="sm" ta="center">
            <Anchor component={Link} to="/login">Back to Login</Anchor>
          </Text>
        </Stack>
      </Card>
    </Center>
  )
}
