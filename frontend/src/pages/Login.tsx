import { Center, Card, TextInput, PasswordInput, Button, Title, Stack, Alert } from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconAlertCircle } from '@tabler/icons-react'
import { useLogin } from '../hooks/useAuth'

export default function Login() {
  const loginMutation = useLogin()
  const form = useForm({
    initialValues: { username: '', password: '' },
    validate: {
      username: (v) => (v.length > 0 ? null : 'Username is required'),
      password: (v) => (v.length > 0 ? null : 'Password is required'),
    },
  })

  return (
    <Center h="100vh" bg="gray.1">
      <Card shadow="md" p="xl" w={400}>
        <Stack>
          <Title order={2} ta="center">OpportunityScraper</Title>
          {loginMutation.isError && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Login failed">
              {(loginMutation.error as any)?.response?.data?.detail || 'Invalid credentials'}
            </Alert>
          )}
          <form onSubmit={form.onSubmit((values) => loginMutation.mutate(values))}>
            <Stack>
              <TextInput label="Username" placeholder="Enter username" {...form.getInputProps('username')} />
              <PasswordInput label="Password" placeholder="Enter password" {...form.getInputProps('password')} />
              <Button type="submit" fullWidth loading={loginMutation.isPending}>
                Login
              </Button>
            </Stack>
          </form>
        </Stack>
      </Card>
    </Center>
  )
}
